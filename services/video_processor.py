import cv2
import numpy as np
import uuid
import os
import json

# Lazy-load YOLO model to avoid crash if ultralytics/network unavailable
_yolo_model = None

def _get_yolo():
    global _yolo_model
    if _yolo_model is None:
        try:
            from ultralytics import YOLO
            # Prefer higher-accuracy medium model; fallback to nano for reliability.
            model_path = "yolov8m.pt" if os.path.exists("yolov8m.pt") else "yolov8n.pt"
            _yolo_model = YOLO(model_path)
            print(f"✅ YOLO model loaded ({model_path}).")
        except Exception as e:
            print(f"⚠️ YOLO not available: {e}. Detection will return empty results.")
    return _yolo_model


def _get_target_classes():
    """
    Parse target class IDs from env. Example:
    SPATIAL_TARGET_CLASSES=0,24,26,28,39,41,56,57,58,59,60,62,63,64,65,66,67,73,74
    """
    raw = os.getenv(
        "SPATIAL_TARGET_CLASSES",
        # Medium expansion for indoor demos: furniture + common desktop/handheld items.
        "0,24,26,28,39,41,56,57,58,59,60,62,63,64,65,66,67,73,74"
    )
    ids = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            ids.append(int(item))
        except ValueError:
            continue
    return ids or [0, 24, 26, 28, 39, 41, 56, 57, 58, 59, 60, 62, 63, 64, 65, 66, 67, 73, 74]

def process_frame(
    image_bytes: bytes, 
    center_depth: float, 
    pose_str: str,
    scan_id: str,
    run_detection: bool = True,
    return_frame_path: bool = False
):
    """
    Process a single frame:
    1. Save raw image
    2. Detect objects (YOLO)
    3. Calculate 3D coordinates for each object
    4. Return list of detected objects
    """
    
    # 1. Decode & Save Image
    nparr = np.frombuffer(image_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if frame is None:
        return []
    
    frame_filename = f"frame_{uuid.uuid4().hex[:8]}.jpg"
    save_dir = f"data/frames/{scan_id}"
    os.makedirs(save_dir, exist_ok=True)
    frame_path = os.path.join(save_dir, frame_filename)
    cv2.imwrite(frame_path, frame)
    
    img_h, img_w, _ = frame.shape
    
    # 2. Parse Pose Matrix (4x4 flattened -> 4x4 numpy)
    pose = np.eye(4)
    try:
        values = [float(x) for x in pose_str.split(",")]
        if len(values) == 16:
            pose = np.array(values).reshape(4, 4).T
    except:
        print("Warning: Failed to parse pose matrix, using identity.")

    # 3. Detect Objects
    if not run_detection:
        return ([], frame_path) if return_frame_path else []

    model = _get_yolo()
    if model is None:
        # No YOLO: return a dummy detection with the saved frame path
        detections = [{
            "label": "unprocessed_frame",
            "confidence": 0.0,
            "bbox": [0, 0, img_w, img_h],
            "position_3d": {"x": 0.0, "y": 0.0, "z": float(center_depth)},
            "frame_path": frame_path
        }]
        return (detections, frame_path) if return_frame_path else detections
    
    # Stable demo default: constrained but configurable class whitelist.
    target_classes = _get_target_classes()
    detect_conf = float(os.getenv("SPATIAL_DETECT_CONF", "0.35"))
    max_det = int(os.getenv("SPATIAL_MAX_DETECTIONS", "30"))
    imgsz = int(os.getenv("SPATIAL_MODEL_IMGSZ", "640"))
    use_tracking = os.getenv("SPATIAL_USE_TRACKING", "1").strip().lower() not in {"0", "false", "no"}

    # Use TRACKING to get stable IDs (persist=True)
    # This aligns with the "Persistence Buffer" architecture.
    try:
        if use_tracking:
            results = model.track(
                frame,
                persist=True,
                verbose=False,
                classes=target_classes,
                tracker="bytetrack.yaml",
                conf=detect_conf,
                max_det=max_det,
                imgsz=imgsz
            )
        else:
            results = model(
                frame,
                verbose=False,
                classes=target_classes,
                conf=detect_conf,
                max_det=max_det,
                imgsz=imgsz
            )
    except Exception as e:
        # Fallback if tracking fails (e.g. tracker config missing)
        print(f"Tracking failed, falling back to predict: {e}")
        results = model(
            frame,
            verbose=False,
            classes=target_classes,
            conf=detect_conf,
            max_det=max_det,
            imgsz=imgsz
        )

    detections = []
    
    for r in results:
        boxes = r.boxes
        if boxes is None:
            continue
            
        for box in boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            confidence = float(box.conf[0])
            cls = int(box.cls[0])
            label = model.names[cls]
            
            # Get Track ID (might be None if tracking unsure)
            track_id = int(box.id[0]) if (box.id is not None) else -1
            
            u = (x1 + x2) / 2
            v = (y1 + y2) / 2
            
            fx = img_w * 1.5 
            fy = fx
            cx = img_w / 2
            cy = img_h / 2
            
            Zc = -center_depth
            Xc = (u - cx) * center_depth / fx
            Yc = -(v - cy) * center_depth / fy
            
            P_cam = np.array([Xc, Yc, Zc, 1.0])
            P_world = pose @ P_cam
            
            detections.append({
                "label": label,
                "confidence": confidence,
                "track_id": track_id,  # NEW
                "bbox": [int(x1), int(y1), int(x2), int(y2)],
                "position_3d": {
                    "x": float(P_world[0]),
                    "y": float(P_world[1]),
                    "z": float(P_world[2])
                },
                "frame_path": frame_path
            })
            
    return (detections, frame_path) if return_frame_path else detections


def crop_detections(image_bytes: bytes, detections: list, min_size: int = 32):
    """Crop each detected object from the frame. Returns list of JPEG bytes per detection."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if frame is None:
        return [None] * len(detections)

    img_h, img_w = frame.shape[:2]
    crops = []
    for d in detections:
        bbox = d.get("bbox", [0, 0, 0, 0])
        x1, y1, x2, y2 = bbox
        # Pad 10% for context
        pad_x = int((x2 - x1) * 0.1)
        pad_y = int((y2 - y1) * 0.1)
        x1 = max(0, x1 - pad_x)
        y1 = max(0, y1 - pad_y)
        x2 = min(img_w, x2 + pad_x)
        y2 = min(img_h, y2 + pad_y)

        if (x2 - x1) < min_size or (y2 - y1) < min_size:
            crops.append(None)
            continue

        crop = frame[y1:y2, x1:x2]
        _, buf = cv2.imencode(".jpg", crop)
        crops.append(buf.tobytes())
    return crops

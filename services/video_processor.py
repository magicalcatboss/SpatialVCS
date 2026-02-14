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
            _yolo_model = YOLO("yolov8n.pt")
            print("✅ YOLO model loaded.")
        except Exception as e:
            print(f"⚠️ YOLO not available: {e}. Detection will return empty results.")
    return _yolo_model

def process_frame(
    image_bytes: bytes, 
    center_depth: float, 
    pose_str: str,
    scan_id: str
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
    model = _get_yolo()
    if model is None:
        # No YOLO: return a dummy detection with the saved frame path
        return [{
            "label": "unprocessed_frame",
            "confidence": 0.0,
            "bbox": [0, 0, img_w, img_h],
            "position_3d": {"x": 0.0, "y": 0.0, "z": float(center_depth)},
            "frame_path": frame_path
        }]
    
    results = model(frame, verbose=False)
    detections = []
    
    for r in results:
        boxes = r.boxes
        for box in boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            confidence = float(box.conf[0])
            cls = int(box.cls[0])
            label = model.names[cls]
            
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
                "bbox": [int(x1), int(y1), int(x2), int(y2)],
                "position_3d": {
                    "x": float(P_world[0]),
                    "y": float(P_world[1]),
                    "z": float(P_world[2])
                },
                "frame_path": frame_path
            })
            
    return detections

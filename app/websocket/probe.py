import asyncio
import base64
import time
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import get_settings
from app.dependencies import get_optional_gemini, get_scan_store, get_socket_manager, get_spatial_memory
from app.services.pose import object_key_from_detection, pose_matrix_str_from_orientation
from services.llm import GeminiClient
from services.video_processor import crop_detections, process_frame

router = APIRouter()


@router.websocket("/ws/probe/{client_id}")
async def websocket_probe(websocket: WebSocket, client_id: str, api_key: Optional[str] = None):
    settings = get_settings()
    scan_store = get_scan_store()
    socket_manager = get_socket_manager()
    spatial_memory = get_spatial_memory()

    await socket_manager.connect_probe(websocket, client_id)

    final_key = api_key or settings.gemini_api_key
    gemini = GeminiClient(final_key) if final_key else None
    frame_count = 0

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "auth":
                msg_key = data.get("api_key")
                if msg_key:
                    gemini = get_optional_gemini(msg_key)
                    await socket_manager.send_to_probe(client_id, {"type": "auth_ack"})
                continue

            if data.get("type") == "stop_scan":
                scan_id = data.get("scan_id", f"scan_{client_id}")
                if scan_store.get(scan_id) is not None:
                    scan_store.mark_completed(scan_id)
                await socket_manager.broadcast_to_dashboards(
                    {
                        "type": "scan_completed",
                        "scan_id": scan_id,
                        "log": f"Scan {scan_id} completed.",
                    }
                )
                continue

            if data.get("type") != "frame":
                continue

            frame_api_key = data.get("api_key")
            if frame_api_key:
                try:
                    gemini = get_optional_gemini(frame_api_key)
                except Exception:
                    pass

            scan_id = data.get("scan_id", f"scan_{client_id}")
            timestamp = data.get("timestamp", time.time())
            frame_count += 1

            image_b64 = data.get("image", "")
            if "," in image_b64:
                image_b64 = image_b64.split(",", 1)[1]
            try:
                image_bytes = base64.b64decode(image_b64)
            except Exception:
                await socket_manager.send_to_probe(
                    client_id,
                    {"type": "error", "message": "Invalid base64 image"},
                )
                continue

            pose_data = data.get("pose", {})
            alpha = float(pose_data.get("alpha", 0) or 0)
            beta = float(pose_data.get("beta", 0) or 0)
            gamma = float(pose_data.get("gamma", 0) or 0)
            pose_str = pose_matrix_str_from_orientation(alpha, beta, gamma)
            estimated_depth = 1.5

            detections = []
            frame_path = ""
            should_run_yolo = frame_count % settings.yolo_frame_stride == 1
            if should_run_yolo:
                detections, frame_path = process_frame(
                    image_bytes, estimated_depth, pose_str, scan_id, return_frame_path=True
                )
            else:
                _, frame_path = process_frame(
                    image_bytes,
                    estimated_depth,
                    pose_str,
                    scan_id,
                    run_detection=False,
                    return_frame_path=True,
                )

            gemini_objects = []
            run_gemini = gemini and (frame_count % settings.gemini_frame_stride == 1)
            if run_gemini and detections:
                try:
                    crops = crop_detections(image_bytes, detections)
                    pairs = [(c, d) for c, d in zip(crops, detections) if c is not None]
                    pairs = pairs[: settings.max_gemini_crops]

                    async def describe_crop(crop, det):
                        desc = await asyncio.to_thread(gemini.describe_crop, crop, det["label"])
                        return desc, det

                    results = await asyncio.gather(*[describe_crop(c, d) for c, d in pairs])
                    for desc, det in results:
                        gemini_obj = {
                            "name": desc.get("name", det["label"]),
                            "position": det.get("position_3d", {}),
                            "details": desc.get("details", ""),
                            "bbox": det.get("bbox"),
                            "track_id": det.get("track_id", -1),
                            "yolo_label": det["label"],
                            "confidence": det["confidence"],
                        }
                        gemini_objects.append(gemini_obj)
                        det["gemini_name"] = gemini_obj["name"]
                        det["gemini_details"] = gemini_obj["details"]
                except Exception as exc:
                    print(f"Gemini crop error: {exc}")

            scan_record = scan_store.ensure(scan_id, source=client_id)
            scan_store.increment_frames(scan_id, frame_path or (detections[0].get("frame_path") if detections else None))
            scan_record.updated_at = timestamp

            if detections:
                scan_store.record_detections(scan_id, detections, timestamp)

            stored_objects = []
            for obj in gemini_objects:
                meta = {
                    "scan_id": scan_id,
                    "frame_path": frame_path or (detections[0]["frame_path"] if detections else ""),
                    "timestamp": timestamp,
                    "bbox": obj.get("bbox"),
                    "track_id": obj.get("track_id", -1),
                    "yolo_label": obj.get("yolo_label", ""),
                    "confidence": obj.get("confidence", 0),
                    "position_3d": obj.get("position"),
                    "source": client_id,
                }
                text_to_index = f"{obj.get('name', '')} {obj.get('details', '')}"
                try:
                    spatial_memory.add_observation(text_to_index, meta)
                except Exception as exc:
                    print(f"Spatial memory add failed: {exc}")
                stored_objects.append(
                    {
                        "name": obj.get("name", ""),
                        "position": obj.get("position", {}),
                        "details": obj.get("details", ""),
                        "timestamp": timestamp,
                        "frame_path": meta["frame_path"],
                        "bbox": obj.get("bbox"),
                        "track_id": obj.get("track_id", -1),
                        "yolo_label": obj.get("yolo_label", ""),
                        "confidence": obj.get("confidence", 0),
                    }
                )

            if stored_objects:
                scan_store.record_gemini_objects(scan_id, stored_objects, timestamp)

            broadcast_objects = []
            state_vector = {}
            gemini_label_cache = {
                key: value.model_dump() if hasattr(value, "model_dump") else dict(value)
                for key, value in scan_record.gemini_label_cache.items()
            }

            for det in detections:
                tid = det.get("track_id", -1)
                label = det["label"]
                obj_key = object_key_from_detection(det)

                if det.get("gemini_name"):
                    gemini_label_cache[obj_key] = {
                        "name": det.get("gemini_name", label),
                        "details": det.get("gemini_details", ""),
                        "updated_at": float(timestamp),
                    }

                cached = gemini_label_cache.get(obj_key)
                if cached and (float(timestamp) - float(cached.get("updated_at", 0.0)) <= settings.gemini_label_ttl_sec):
                    display_label = cached.get("name", label)
                    display_details = cached.get("details", det.get("gemini_details", ""))
                else:
                    display_label = det.get("gemini_name", label)
                    display_details = det.get("gemini_details", "")
                    if cached:
                        gemini_label_cache.pop(obj_key, None)

                state_vector[obj_key] = {
                    "x": det.get("position_3d", {}).get("x", 0),
                    "y": det.get("position_3d", {}).get("y", 0),
                    "z": det.get("position_3d", {}).get("z", 0),
                    "confidence": det["confidence"],
                    "track_id": tid,
                    "label": display_label,
                    "yolo_label": det["label"],
                }

                broadcast_objects.append(
                    {
                        "label": display_label,
                        "yolo_label": det["label"],
                        "details": display_details,
                        "confidence": det["confidence"],
                        "track_id": tid,
                        "bbox": det.get("bbox"),
                        "position": det.get("position_3d", {"x": 0, "y": 0, "z": estimated_depth}),
                    }
                )

            scan_store.update_gemini_cache(scan_id, gemini_label_cache)

            await socket_manager.broadcast_to_dashboards(
                {
                    "type": "detection",
                    "source": client_id,
                    "scan_id": scan_id,
                    "frame_number": frame_count,
                    "objects": broadcast_objects,
                    "state_vector": state_vector,
                    "gemini_objects": gemini_objects,
                    "pose": {"alpha": alpha, "beta": beta, "gamma": gamma},
                    "timestamp": timestamp,
                    "log": f"[{scan_id}] Frame #{frame_count}: {len(detections)} objects detected",
                }
            )

            await socket_manager.send_to_probe(
                client_id,
                {"type": "ack", "frame": frame_count, "objects_found": len(detections)},
            )

    except WebSocketDisconnect:
        socket_manager.disconnect_probe(client_id)
        try:
            await socket_manager.broadcast_to_dashboards(
                {"type": "probe_disconnected", "source": client_id}
            )
        except Exception:
            pass
    except Exception as exc:
        print(f"Error in probe ws: {exc}")
        socket_manager.disconnect_probe(client_id)

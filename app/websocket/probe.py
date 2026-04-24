import base64
import logging
import time
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import get_settings
from app.dependencies import (
    get_depth_estimator,
    get_identity_resolver,
    get_label_fusion,
    get_optional_gemini,
    get_scan_store,
    get_socket_manager,
    get_spatial_memory,
)
from app.services.gemini_queue import GeminiDescribeJob, get_gemini_queue
from app.services.metrics import metrics
from app.services.pose import pose_matrix_str_from_orientation
from services.llm import GeminiClient
from services.video_processor import crop_detections, process_frame

router = APIRouter()
logger = logging.getLogger(__name__)


def _model_cache_to_dict(cache: dict) -> dict:
    return {
        key: value.model_dump() if hasattr(value, "model_dump") else dict(value)
        for key, value in cache.items()
    }


def _is_fresh_gemini_cache(entry: dict | None, timestamp: float, ttl_sec: float) -> bool:
    if not entry:
        return False
    try:
        return float(timestamp) - float(entry.get("updated_at", 0.0)) <= ttl_sec
    except (TypeError, ValueError):
        return False


@router.websocket("/ws/probe/{client_id}")
async def websocket_probe(websocket: WebSocket, client_id: str, api_key: Optional[str] = None):
    settings = get_settings()
    scan_store = get_scan_store()
    socket_manager = get_socket_manager()
    spatial_memory = get_spatial_memory()
    identity_resolver = get_identity_resolver()
    label_fusion = get_label_fusion()
    depth_estimator = get_depth_estimator()
    gemini_queue = get_gemini_queue()

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
                if await scan_store.get(scan_id) is not None:
                    await scan_store.mark_completed(scan_id)
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
            metrics.inc("spatialvcs_frames_received")
            logger.info("frame_received source=%s scan_id=%s frame=%s", client_id, scan_id, frame_count)

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
            estimated_depth = depth_estimator.estimate(data)

            detections = []
            frame_path = ""
            should_run_yolo = frame_count % settings.yolo_frame_stride == 1
            with metrics.time_block("spatialvcs_frame_processing_seconds"):
                if should_run_yolo:
                    detections, frame_path = process_frame(
                        image_bytes, estimated_depth, pose_str, scan_id, return_frame_path=True
                    )
                    metrics.inc("spatialvcs_yolo_frames")
                    metrics.inc("spatialvcs_yolo_detections", len(detections))
                    logger.info("yolo_processed source=%s scan_id=%s frame=%s detections=%s", client_id, scan_id, frame_count, len(detections))
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

            for det in detections:
                obj_key = identity_resolver.resolve(scan_id, det, float(timestamp))
                det["object_key"] = obj_key
                logger.info("identity_matched scan_id=%s object_key=%s label=%s", scan_id, obj_key, det.get("label", ""))

            scan_record = await scan_store.ensure(scan_id, source=client_id)
            await scan_store.increment_frames(scan_id, frame_path or (detections[0].get("frame_path") if detections else None))
            scan_record.updated_at = timestamp
            gemini_label_cache = _model_cache_to_dict(scan_record.gemini_label_cache)

            if detections:
                try:
                    await scan_store.record_detections(scan_id, detections, timestamp)
                except Exception as exc:
                    metrics.inc("spatialvcs_db_write_errors")
                    logger.warning("db_write_failed scan_id=%s error=%s", scan_id, exc)

            if run_gemini and detections:
                try:
                    crops = crop_detections(image_bytes, detections)
                    pairs = [(c, d) for c, d in zip(crops, detections) if c is not None]
                    for crop, det in pairs[: settings.max_gemini_crops]:
                        if _is_fresh_gemini_cache(
                            gemini_label_cache.get(det["object_key"]),
                            float(timestamp),
                            settings.gemini_label_ttl_sec,
                        ):
                            metrics.inc("spatialvcs_gemini_cache_hits")
                            logger.info("gemini_job_cache_hit scan_id=%s object_key=%s", scan_id, det["object_key"])
                            continue
                        enqueued = gemini_queue.enqueue(
                            GeminiDescribeJob(
                                scan_id=scan_id,
                                object_key=det["object_key"],
                                crop_bytes=crop,
                                detection=dict(det),
                                frame_path=frame_path or det.get("frame_path", ""),
                                timestamp=float(timestamp),
                                source=client_id,
                                gemini=gemini,
                                scan_store=scan_store,
                                spatial_memory=spatial_memory,
                            )
                        )
                        logger.info("gemini_job_%s scan_id=%s object_key=%s", "queued" if enqueued else "skipped", scan_id, det["object_key"])
                except Exception as exc:
                    metrics.inc("spatialvcs_gemini_jobs_failed")
                    logger.warning("gemini_queue_failed scan_id=%s error=%s", scan_id, exc)

            broadcast_objects = []
            state_vector = {}

            for det in detections:
                tid = det.get("track_id", -1)
                obj_key = det.get("object_key") or identity_resolver.resolve(scan_id, det, float(timestamp))

                cached = gemini_label_cache.get(obj_key)
                fused = label_fusion.fuse(det, cached, float(timestamp), settings.gemini_label_ttl_sec)
                display_label = fused.display_label
                display_details = fused.details
                if cached and fused.label_source != "gemini_cache":
                    display_details = det.get("gemini_details", "")
                    if cached:
                        gemini_label_cache.pop(obj_key, None)

                state_vector[obj_key] = {
                    "object_key": obj_key,
                    "x": det.get("position_3d", {}).get("x", 0),
                    "y": det.get("position_3d", {}).get("y", 0),
                    "z": det.get("position_3d", {}).get("z", 0),
                    "confidence": det["confidence"],
                    "track_id": tid,
                    "label": display_label,
                    "yolo_label": det["label"],
                    "canonical_label": fused.canonical_label,
                    "label_confidence": fused.label_confidence,
                    "label_source": fused.label_source,
                }

                broadcast_objects.append(
                    {
                        "object_key": obj_key,
                        "label": display_label,
                        "yolo_label": det["label"],
                        "canonical_label": fused.canonical_label,
                        "details": display_details,
                        "confidence": det["confidence"],
                        "label_confidence": fused.label_confidence,
                        "label_source": fused.label_source,
                        "track_id": tid,
                        "bbox": det.get("bbox"),
                        "position": det.get("position_3d", {"x": 0, "y": 0, "z": estimated_depth}),
                    }
                )

            await scan_store.update_gemini_cache(scan_id, gemini_label_cache)

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

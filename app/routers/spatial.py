import os
import time
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.dependencies import get_gemini_client, get_scan_store, get_socket_manager, get_spatial_memory
from app.schemas.scan import ScanMemoryResponse, ScansResponse
from app.schemas.spatial import (
    ProcessFrameResponse,
    ResetResponse,
    SpatialDiffRequest,
    SpatialDiffResponse,
    SpatialQueryRequest,
    SpatialQueryResponse,
)
from app.services.pose import euclidean_distance
from app.services.cross_scan_matching import build_cross_scan_matches
from app.services.scan_store import ScanStore
from services.llm import GeminiClient
from services.socket_manager import ConnectionManager
from services.spatial_memory import SpatialMemory
from services.video_processor import process_frame

router = APIRouter(tags=["spatial"])


@router.post("/spatial/scan/frame", response_model=ProcessFrameResponse)
async def receive_frame(
    scan_id: str = Form(...),
    center_depth: float = Form(...),
    pose: str = Form(...),
    image: UploadFile = File(...),
    client: Annotated[GeminiClient, Depends(get_gemini_client)] = None,
    scan_store: Annotated[ScanStore, Depends(get_scan_store)] = None,
    spatial_memory: Annotated[SpatialMemory, Depends(get_spatial_memory)] = None,
):
    timestamp = time.time()

    image_bytes = await image.read()
    detections = process_frame(image_bytes, center_depth, pose, scan_id)
    await scan_store.ensure(scan_id, source="rest")
    await scan_store.increment_frames(scan_id, detections[0].get("frame_path") if detections else None)
    record = await scan_store.get(scan_id)
    if record is not None:
        record.updated_at = timestamp

    if detections:
        await scan_store.record_detections(scan_id, detections, timestamp)

        description_data = client.describe_for_spatial(image_bytes)
        gemini_objects = description_data.get("objects", [])

        stored_objects = []
        for obj in gemini_objects:
            meta = {
                "scan_id": scan_id,
                "frame_path": detections[0]["frame_path"],
                "timestamp": timestamp,
                "yolo_detections": detections,
                "details": obj,
            }
            text_to_index = f"{obj.get('name', '')} {obj.get('position', '')} {obj.get('details', '')}"
            spatial_memory.add_observation(text_to_index, meta)
            stored_objects.append(
                {
                    "name": obj.get("name", ""),
                    "position": obj.get("position", {}),
                    "details": obj.get("details", ""),
                    "timestamp": timestamp,
                    "frame_path": detections[0]["frame_path"],
                }
            )

        if stored_objects:
            await scan_store.record_gemini_objects(scan_id, stored_objects, timestamp)

    return {"status": "processed", "objects_found": len(detections)}


@router.post("/spatial/query", response_model=SpatialQueryResponse)
async def spatial_query(
    request: SpatialQueryRequest,
    client: Annotated[GeminiClient, Depends(get_gemini_client)] = None,
    spatial_memory: Annotated[SpatialMemory, Depends(get_spatial_memory)] = None,
):
    results = spatial_memory.search(request.query, request.top_k, scan_id=request.scan_id)
    answer = client.answer_spatial_query(request.query, results)

    formatted_results = []
    for r in results:
        meta = r["metadata"]
        frame_filename = os.path.basename(meta.get("frame_path", ""))
        scan_id = meta.get("scan_id", "unknown")
        frame_url = f"/spatial/frame/{scan_id}/{frame_filename}"

        formatted_results.append(
            {
                "score": r["score"],
                "description": r["description"],
                "frame_url": frame_url,
                "yolo_data": meta.get("yolo_detections", []),
                "position": meta.get("position_3d"),
                "yolo_label": meta.get("yolo_label", ""),
                "track_id": int(meta.get("track_id", -1) or -1),
            }
        )

    return {
        "query": request.query,
        "answer": answer.get("answer"),
        "results": formatted_results,
    }


@router.get("/spatial/frame/{scan_id}/{filename}")
def get_frame(scan_id: str, filename: str):
    if filename != os.path.basename(filename):
        raise HTTPException(status_code=400, detail="Invalid frame filename")
    path = f"data/frames/{scan_id}/{filename}"
    if os.path.exists(path):
        return FileResponse(path)
    raise HTTPException(status_code=404, detail="Frame not found")


@router.post("/spatial/diff", response_model=SpatialDiffResponse)
async def spatial_diff(
    request: SpatialDiffRequest,
    scan_store: Annotated[ScanStore, Depends(get_scan_store)] = None,
):
    for sid in [request.scan_id_before, request.scan_id_after]:
        if await scan_store.get(sid) is None:
            raise HTTPException(status_code=404, detail=f"Scan '{sid}' not found")

    before_latest = await scan_store.latest_by_label(request.scan_id_before)
    after_latest = await scan_store.latest_by_label(request.scan_id_after)

    before_labels = set(before_latest.keys())
    after_labels = set(after_latest.keys())
    common_labels = before_labels & after_labels

    events = []
    for label in sorted(common_labels):
        old_pos = before_latest[label].get("position_3d", {})
        new_pos = after_latest[label].get("position_3d", {})
        dist = euclidean_distance(new_pos, old_pos)
        if dist > request.threshold:
            events.append(
                {
                    "type": "MOVE",
                    "label": label,
                    "distance": round(dist, 4),
                    "from": old_pos,
                    "to": new_pos,
                }
            )

    for label in sorted(after_labels - before_labels):
        events.append(
            {
                "type": "ADDED",
                "label": label,
                "distance": None,
                "from": None,
                "to": after_latest[label].get("position_3d", {}),
            }
        )

    for label in sorted(before_labels - after_labels):
        events.append(
            {
                "type": "REMOVED",
                "label": label,
                "distance": None,
                "from": before_latest[label].get("position_3d", {}),
                "to": None,
            }
        )

    summary = f"{len(events)} changes detected (threshold={request.threshold}m)."
    return {
        "before_scan": request.scan_id_before,
        "after_scan": request.scan_id_after,
        "threshold": request.threshold,
        "change_count": len(events),
        "events": events,
        "summary": summary,
    }


@router.delete("/spatial/reset", response_model=ResetResponse)
async def reset_spatial_data(
    _: Annotated[GeminiClient, Depends(get_gemini_client)],
    spatial_memory: Annotated[SpatialMemory, Depends(get_spatial_memory)] = None,
    scan_store: Annotated[ScanStore, Depends(get_scan_store)] = None,
    socket_manager: Annotated[ConnectionManager, Depends(get_socket_manager)] = None,
):
    spatial_memory.reset_database()
    await scan_store.clear()
    await socket_manager.broadcast_to_dashboards(
        {
            "type": "system_reset",
            "log": "SYSTEM RESET: All spatial memory cleared.",
        }
    )
    return {"status": "ok", "message": "Spatial memory cleared"}


@router.get("/spatial/scans", response_model=ScansResponse)
async def list_scans(scan_store: Annotated[ScanStore, Depends(get_scan_store)] = None):
    return {"scans": await scan_store.list_summaries()}


@router.get("/spatial/memory/{scan_id}", response_model=ScanMemoryResponse)
async def get_memory(scan_id: str, scan_store: Annotated[ScanStore, Depends(get_scan_store)] = None):
    record = await scan_store.get(scan_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Scan '{scan_id}' not found")
    return record


@router.get("/spatial/matches/{scan_id}")
async def get_cross_scan_matches(scan_id: str, scan_store: Annotated[ScanStore, Depends(get_scan_store)] = None):
    if not hasattr(scan_store, "list_spatial_objects"):
        return {"scan_id": scan_id, "matches": [], "mode": "memory_store_no_pgvector"}
    source_objects = await scan_store.list_spatial_objects(scan_id)
    candidate_objects = await scan_store.list_spatial_objects(None)
    return {
        "scan_id": scan_id,
        "matches": build_cross_scan_matches(source_objects, candidate_objects),
        "mode": "structured_fallback",
    }

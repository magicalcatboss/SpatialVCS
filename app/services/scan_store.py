import os
from typing import Optional, Protocol

from app.schemas.detection import DetectionRecord, GeminiLabelCacheEntry, GeminiObject
from app.schemas.scan import ScanRecord, ScanSummary


class ScanStore(Protocol):
    async def ensure(self, scan_id: str, source: Optional[str] = None) -> ScanRecord: ...
    async def get(self, scan_id: str) -> Optional[ScanRecord]: ...
    async def list_summaries(self) -> list[ScanSummary]: ...
    async def record_detections(self, scan_id: str, dets: list[dict], ts: float) -> None: ...
    async def record_gemini_objects(self, scan_id: str, objs: list[dict], ts: float) -> None: ...
    async def increment_frames(self, scan_id: str, frame_path: Optional[str]) -> None: ...
    async def mark_completed(self, scan_id: str) -> None: ...
    async def update_gemini_cache(self, scan_id: str, cache: dict) -> None: ...
    async def latest_by_label(self, scan_id: str) -> dict[str, dict]: ...
    async def clear(self) -> None: ...


class InMemoryScanStore:
    """Phase A implementation: wraps the current in-memory scan state."""

    def __init__(self):
        self._scans: dict[str, ScanRecord] = {}

    async def ensure(self, scan_id: str, source: Optional[str] = None) -> ScanRecord:
        if scan_id not in self._scans:
            self._scans[scan_id] = ScanRecord(scan_id=scan_id, source=source)
        record = self._scans[scan_id]
        if source is not None and record.source is None:
            record.source = source
        return record

    async def get(self, scan_id: str) -> Optional[ScanRecord]:
        return self._scans.get(scan_id)

    async def list_summaries(self) -> list[ScanSummary]:
        return [
            ScanSummary(
                scan_id=record.scan_id,
                status=record.status,
                source=record.source,
                frames=record.frames,
                object_count=record.object_count,
                detection_count=len(record.detections),
                updated_at=record.updated_at,
                last_frame=os.path.basename(record.last_frame_path or ""),
            )
            for record in self._scans.values()
        ]

    async def record_detections(self, scan_id: str, dets: list[dict], ts: float) -> None:
        record = await self.ensure(scan_id)
        for det in dets:
            record.detections.append(
                DetectionRecord(
                    object_key=det.get("object_key", ""),
                    label=det.get("label", ""),
                    yolo_label=det.get("yolo_label", det.get("label", "")),
                    gemini_name=det.get("gemini_name", ""),
                    confidence=float(det.get("confidence", 0.0)),
                    position_3d=det.get("position_3d", {}) or {},
                    timestamp=ts,
                    frame_path=det.get("frame_path", ""),
                )
            )

    async def record_gemini_objects(self, scan_id: str, objs: list[dict], ts: float) -> None:
        record = await self.ensure(scan_id)
        for obj in objs:
            payload = dict(obj)
            payload.setdefault("timestamp", ts)
            record.objects.append(GeminiObject(**payload))
        record.object_count += len(objs)

    async def increment_frames(self, scan_id: str, frame_path: Optional[str]) -> None:
        record = await self.ensure(scan_id)
        record.frames += 1
        if frame_path:
            record.last_frame_path = frame_path

    async def mark_completed(self, scan_id: str) -> None:
        record = await self.ensure(scan_id)
        record.status = "completed"

    async def update_gemini_cache(self, scan_id: str, cache: dict) -> None:
        record = await self.ensure(scan_id)
        record.gemini_label_cache = {
            key: value if isinstance(value, GeminiLabelCacheEntry) else GeminiLabelCacheEntry(**value)
            for key, value in cache.items()
        }

    async def latest_by_label(self, scan_id: str) -> dict[str, dict]:
        record = await self.get(scan_id)
        if record is None:
            return {}

        latest: dict[str, DetectionRecord] = {}
        for item in record.detections:
            label = item.yolo_label or item.label
            if not label:
                continue
            prev = latest.get(label)
            if prev is None or float(item.timestamp) > float(prev.timestamp):
                latest[label] = item
        return {label: item.model_dump() for label, item in latest.items()}

    async def clear(self) -> None:
        self._scans.clear()

import os
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.models.observation import ObservationModel
from app.db.models.scan import ScanModel
from app.db.models.spatial_object import SpatialObjectModel
from app.schemas.detection import GeminiLabelCacheEntry
from app.schemas.scan import ScanRecord, ScanSummary
from app.services.pose import object_key_from_detection


def _dt_to_timestamp(value: datetime | None) -> float | None:
    if value is None:
        return None
    return value.timestamp()


def _timestamp_to_dt(value: float) -> datetime:
    return datetime.fromtimestamp(float(value), tz=UTC)


class PostgresScanStore:
    def __init__(self, sessionmaker: async_sessionmaker):
        self._sessionmaker = sessionmaker
        self._gemini_caches: dict[str, dict[str, GeminiLabelCacheEntry]] = {}

    async def ensure(self, scan_id: str, source: Optional[str] = None) -> ScanRecord:
        async with self._sessionmaker() as session:
            scan = await session.scalar(select(ScanModel).where(ScanModel.scan_id == scan_id))
            if scan is None:
                scan = ScanModel(scan_id=scan_id, source=source, updated_at=datetime.now(UTC))
                session.add(scan)
                await session.commit()
            elif source is not None and scan.source is None:
                scan.source = source
                await session.commit()
            return await self._record_from_scan(scan)

    async def get(self, scan_id: str) -> Optional[ScanRecord]:
        async with self._sessionmaker() as session:
            scan = await session.scalar(select(ScanModel).where(ScanModel.scan_id == scan_id))
            if scan is None:
                return None
            return await self._record_from_scan(scan, include_children=True)

    async def list_summaries(self) -> list[ScanSummary]:
        async with self._sessionmaker() as session:
            obs_counts = (
                select(
                    ObservationModel.scan_id,
                    func.count(ObservationModel.id).label("detection_count"),
                )
                .group_by(ObservationModel.scan_id)
                .subquery()
            )
            rows = (
                await session.execute(
                    select(ScanModel, obs_counts.c.detection_count)
                    .outerjoin(obs_counts, ScanModel.scan_id == obs_counts.c.scan_id)
                    .order_by(ScanModel.started_at.desc())
                )
            ).all()
            return [
                ScanSummary(
                    scan_id=scan.scan_id,
                    status=scan.status,
                    source=scan.source,
                    frames=scan.frame_count,
                    object_count=scan.object_count,
                    detection_count=int(detection_count or 0),
                    updated_at=_dt_to_timestamp(scan.updated_at),
                    last_frame=os.path.basename(scan.last_frame_path or ""),
                )
                for scan, detection_count in rows
            ]

    async def record_detections(self, scan_id: str, dets: list[dict], ts: float) -> None:
        if not dets:
            return
        await self.ensure(scan_id)
        seen_at = _timestamp_to_dt(ts)
        async with self._sessionmaker() as session:
            for det in dets:
                object_key = object_key_from_detection(det)
                label = det.get("label", "object")
                yolo_label = det.get("yolo_label", label)
                values = {
                    "scan_id": scan_id,
                    "object_key": object_key,
                    "track_id": int(det.get("track_id", -1)),
                    "canonical_label": det.get("gemini_name") or yolo_label or label,
                    "yolo_label": yolo_label,
                    "gemini_name": det.get("gemini_name"),
                    "gemini_details": det.get("gemini_details"),
                    "confidence": float(det.get("confidence", 0.0)),
                    "last_position": det.get("position_3d") or {},
                    "last_bbox": det.get("bbox"),
                    "last_seen_at": seen_at,
                }
                stmt = (
                    insert(SpatialObjectModel)
                    .values(**values)
                    .on_conflict_do_update(
                        constraint="idx_obj_scan_key",
                        set_={
                            "track_id": values["track_id"],
                            "canonical_label": values["canonical_label"],
                            "yolo_label": values["yolo_label"],
                            "gemini_name": values["gemini_name"],
                            "gemini_details": values["gemini_details"],
                            "confidence": values["confidence"],
                            "last_position": values["last_position"],
                            "last_bbox": values["last_bbox"],
                            "last_seen_at": values["last_seen_at"],
                        },
                    )
                    .returning(SpatialObjectModel.id)
                )
                object_id = await session.scalar(stmt)
                session.add(
                    ObservationModel(
                        object_id=object_id,
                        scan_id=scan_id,
                        track_id=int(det.get("track_id", -1)),
                        yolo_label=yolo_label,
                        gemini_name=det.get("gemini_name"),
                        confidence=float(det.get("confidence", 0.0)),
                        bbox=det.get("bbox"),
                        position_3d=det.get("position_3d") or {},
                        frame_path=det.get("frame_path", ""),
                        timestamp=ts,
                    )
                )
            await session.execute(
                update(ScanModel)
                .where(ScanModel.scan_id == scan_id)
                .values(updated_at=seen_at)
            )
            await session.commit()

    async def record_gemini_objects(self, scan_id: str, objs: list[dict], ts: float) -> None:
        if not objs:
            return
        await self.ensure(scan_id)
        seen_at = _timestamp_to_dt(ts)
        async with self._sessionmaker() as session:
            for obj in objs:
                object_key = f"gemini_{obj.get('track_id', -1)}_{obj.get('name', 'object')}"
                values = {
                    "scan_id": scan_id,
                    "object_key": object_key,
                    "track_id": int(obj.get("track_id", -1)),
                    "canonical_label": obj.get("name") or obj.get("yolo_label") or "object",
                    "yolo_label": obj.get("yolo_label", ""),
                    "gemini_name": obj.get("name", ""),
                    "gemini_details": obj.get("details", ""),
                    "confidence": float(obj.get("confidence", 0.0)),
                    "last_position": obj.get("position") if isinstance(obj.get("position"), dict) else None,
                    "last_bbox": obj.get("bbox"),
                    "last_seen_at": seen_at,
                }
                await session.execute(
                    insert(SpatialObjectModel)
                    .values(**values)
                    .on_conflict_do_update(
                        constraint="idx_obj_scan_key",
                        set_={
                            "canonical_label": values["canonical_label"],
                            "yolo_label": values["yolo_label"],
                            "gemini_name": values["gemini_name"],
                            "gemini_details": values["gemini_details"],
                            "confidence": values["confidence"],
                            "last_position": values["last_position"],
                            "last_bbox": values["last_bbox"],
                            "last_seen_at": values["last_seen_at"],
                        },
                    )
                )
            await session.execute(
                update(ScanModel)
                .where(ScanModel.scan_id == scan_id)
                .values(object_count=ScanModel.object_count + len(objs), updated_at=seen_at)
            )
            await session.commit()

    async def increment_frames(self, scan_id: str, frame_path: Optional[str]) -> None:
        await self.ensure(scan_id)
        values = {"frame_count": ScanModel.frame_count + 1, "updated_at": datetime.now(UTC)}
        if frame_path:
            values["last_frame_path"] = frame_path
        async with self._sessionmaker() as session:
            await session.execute(update(ScanModel).where(ScanModel.scan_id == scan_id).values(**values))
            await session.commit()

    async def mark_completed(self, scan_id: str) -> None:
        await self.ensure(scan_id)
        now = datetime.now(UTC)
        async with self._sessionmaker() as session:
            await session.execute(
                update(ScanModel)
                .where(ScanModel.scan_id == scan_id)
                .values(status="completed", completed_at=now, updated_at=now)
            )
            await session.commit()

    async def update_gemini_cache(self, scan_id: str, cache: dict) -> None:
        self._gemini_caches[scan_id] = {
            key: value if isinstance(value, GeminiLabelCacheEntry) else GeminiLabelCacheEntry(**value)
            for key, value in cache.items()
        }

    async def latest_by_label(self, scan_id: str) -> dict[str, dict]:
        async with self._sessionmaker() as session:
            rows = (
                await session.execute(
                    select(ObservationModel)
                    .where(ObservationModel.scan_id == scan_id)
                    .order_by(ObservationModel.timestamp.asc())
                )
            ).scalars()
            latest: dict[str, ObservationModel] = {}
            for item in rows:
                label = item.yolo_label
                if not label:
                    continue
                prev = latest.get(label)
                if prev is None or float(item.timestamp) > float(prev.timestamp):
                    latest[label] = item
            return {
                label: {
                    "label": item.yolo_label or "",
                    "yolo_label": item.yolo_label or "",
                    "gemini_name": item.gemini_name or "",
                    "confidence": float(item.confidence or 0.0),
                    "position_3d": item.position_3d or {},
                    "timestamp": item.timestamp,
                    "frame_path": item.frame_path or "",
                }
                for label, item in latest.items()
            }

    async def clear(self) -> None:
        async with self._sessionmaker() as session:
            await session.execute(delete(ScanModel))
            await session.commit()
        self._gemini_caches.clear()

    async def _record_from_scan(self, scan: ScanModel, include_children: bool = False) -> ScanRecord:
        objects = []
        detections = []
        if include_children:
            async with self._sessionmaker() as session:
                object_rows = (
                    await session.execute(
                        select(SpatialObjectModel)
                        .where(SpatialObjectModel.scan_id == scan.scan_id)
                        .order_by(SpatialObjectModel.last_seen_at.asc())
                    )
                ).scalars()
                objects = [
                    {
                        "name": row.gemini_name or row.canonical_label,
                        "position": row.last_position or "",
                        "details": row.gemini_details or "",
                        "bbox": row.last_bbox,
                        "track_id": row.track_id,
                        "yolo_label": row.yolo_label or "",
                        "confidence": row.confidence or 0.0,
                        "timestamp": _dt_to_timestamp(row.last_seen_at),
                        "frame_path": "",
                    }
                    for row in object_rows
                ]
                observation_rows = (
                    await session.execute(
                        select(ObservationModel)
                        .where(ObservationModel.scan_id == scan.scan_id)
                        .order_by(ObservationModel.timestamp.asc())
                    )
                ).scalars()
                detections = [
                    {
                        "label": row.yolo_label or "",
                        "yolo_label": row.yolo_label or "",
                        "gemini_name": row.gemini_name or "",
                        "confidence": float(row.confidence or 0.0),
                        "position_3d": row.position_3d or {},
                        "timestamp": row.timestamp,
                        "frame_path": row.frame_path or "",
                    }
                    for row in observation_rows
                ]
        return ScanRecord(
            scan_id=scan.scan_id,
            status=scan.status,
            source=scan.source,
            frames=scan.frame_count,
            object_count=scan.object_count,
            objects=objects,
            detections=detections,
            gemini_label_cache=self._gemini_caches.get(scan.scan_id, {}),
            last_frame_path=scan.last_frame_path,
            updated_at=_dt_to_timestamp(scan.updated_at),
        )

import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass
from typing import Optional

from app.services.metrics import metrics

logger = logging.getLogger(__name__)


@dataclass
class GeminiDescribeJob:
    scan_id: str
    object_key: str
    crop_bytes: bytes
    detection: dict
    frame_path: str
    timestamp: float
    source: str
    gemini: object
    scan_store: object
    spatial_memory: object

    @property
    def job_key(self) -> str:
        digest = hashlib.sha1(self.crop_bytes).hexdigest()[:16]
        return f"{self.scan_id}:{self.object_key}:{digest}"


class GeminiDescribeQueue:
    def __init__(self, max_size: int = 128, concurrency: int = 2, timeout_sec: float = 10.0):
        self.max_size = max_size
        self.concurrency = concurrency
        self.timeout_sec = timeout_sec
        self._queue: asyncio.Queue[GeminiDescribeJob] = asyncio.Queue(maxsize=max_size)
        self._queued_keys: set[str] = set()
        self._workers: list[asyncio.Task] = []
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        self._started = True
        for idx in range(max(1, self.concurrency)):
            self._workers.append(asyncio.create_task(self._worker(idx)))

    async def stop(self) -> None:
        for task in self._workers:
            task.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        self._started = False

    def enqueue(self, job: GeminiDescribeJob) -> bool:
        job_key = job.job_key
        if job_key in self._queued_keys:
            metrics.inc("spatialvcs_gemini_queue_deduped")
            return False
        if self._queue.full():
            metrics.inc("spatialvcs_gemini_queue_dropped")
            metrics.set_gauge("spatialvcs_gemini_queue_depth", self._queue.qsize())
            return False
        self._queued_keys.add(job_key)
        self._queue.put_nowait(job)
        metrics.inc("spatialvcs_gemini_jobs_queued")
        metrics.set_gauge("spatialvcs_gemini_queue_depth", self._queue.qsize())
        return True

    async def _worker(self, worker_id: int) -> None:
        while True:
            job = await self._queue.get()
            metrics.set_gauge("spatialvcs_gemini_queue_depth", self._queue.qsize())
            started_at = time.perf_counter()
            try:
                await asyncio.wait_for(self._process(job), timeout=self.timeout_sec)
                metrics.inc("spatialvcs_gemini_jobs_completed")
                metrics.observe("spatialvcs_gemini_latency_seconds", time.perf_counter() - started_at)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                metrics.inc("spatialvcs_gemini_jobs_failed")
                logger.warning("gemini_job_failed worker=%s scan_id=%s object_key=%s error=%s", worker_id, job.scan_id, job.object_key, exc)
            finally:
                self._queued_keys.discard(job.job_key)
                self._queue.task_done()
                metrics.set_gauge("spatialvcs_gemini_queue_depth", self._queue.qsize())

    async def _process(self, job: GeminiDescribeJob) -> None:
        desc = await asyncio.to_thread(job.gemini.describe_crop, job.crop_bytes, job.detection.get("label", "object"))
        gemini_obj = {
            "name": desc.get("name", job.detection.get("label", "object")),
            "position": job.detection.get("position_3d", {}),
            "details": desc.get("details", ""),
            "bbox": job.detection.get("bbox"),
            "track_id": job.detection.get("track_id", -1),
            "yolo_label": job.detection.get("label", ""),
            "confidence": job.detection.get("confidence", 0.0),
            "object_key": job.object_key,
        }
        meta = {
            "scan_id": job.scan_id,
            "frame_path": job.frame_path,
            "timestamp": job.timestamp,
            "bbox": gemini_obj.get("bbox"),
            "track_id": gemini_obj.get("track_id", -1),
            "yolo_label": gemini_obj.get("yolo_label", ""),
            "confidence": gemini_obj.get("confidence", 0),
            "position_3d": gemini_obj.get("position"),
            "source": job.source,
            "object_key": job.object_key,
        }
        text_to_index = f"{gemini_obj.get('name', '')} {gemini_obj.get('details', '')}"
        try:
            job.spatial_memory.add_observation(text_to_index, meta)
        except Exception as exc:
            logger.warning("spatial_memory_add_failed scan_id=%s object_key=%s error=%s", job.scan_id, job.object_key, exc)

        await job.scan_store.record_gemini_objects(
            job.scan_id,
            [
                {
                    "name": gemini_obj.get("name", ""),
                    "position": gemini_obj.get("position", {}),
                    "details": gemini_obj.get("details", ""),
                    "timestamp": job.timestamp,
                    "frame_path": job.frame_path,
                    "bbox": gemini_obj.get("bbox"),
                    "track_id": gemini_obj.get("track_id", -1),
                    "yolo_label": gemini_obj.get("yolo_label", ""),
                    "confidence": gemini_obj.get("confidence", 0),
                    "object_key": job.object_key,
                }
            ],
            job.timestamp,
        )
        record = await job.scan_store.get(job.scan_id)
        cache = {}
        if record is not None:
            cache = {
                key: value.model_dump() if hasattr(value, "model_dump") else dict(value)
                for key, value in record.gemini_label_cache.items()
            }
        cache[job.object_key] = {
            "name": gemini_obj.get("name", ""),
            "details": gemini_obj.get("details", ""),
            "updated_at": float(job.timestamp),
        }
        await job.scan_store.update_gemini_cache(job.scan_id, cache)


_queue: Optional[GeminiDescribeQueue] = None


def configure_gemini_queue(max_size: int, concurrency: int, timeout_sec: float) -> GeminiDescribeQueue:
    global _queue
    _queue = GeminiDescribeQueue(max_size=max_size, concurrency=concurrency, timeout_sec=timeout_sec)
    return _queue


def get_gemini_queue() -> GeminiDescribeQueue:
    if _queue is None:
        return configure_gemini_queue(max_size=128, concurrency=2, timeout_sec=10.0)
    return _queue

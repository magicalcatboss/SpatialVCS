from typing import Optional

from fastapi import Header, HTTPException

from app.config import get_settings
from app.services.depth import DepthEstimator
from app.services.gemini_queue import configure_gemini_queue, get_gemini_queue
from app.services.identity import ObjectIdentityResolver
from app.services.label_fusion import LabelFusion
from app.services.scan_store import InMemoryScanStore, ScanStore
from services.llm import GeminiClient
from services.socket_manager import ConnectionManager
from services.spatial_memory import SpatialMemory

_spatial_memory = SpatialMemory()
_socket_manager = ConnectionManager()
_scan_store: ScanStore | None = None
_identity_resolver: ObjectIdentityResolver | None = None
_label_fusion = LabelFusion()
_depth_estimator: DepthEstimator | None = None


def get_spatial_memory() -> SpatialMemory:
    return _spatial_memory


def get_socket_manager() -> ConnectionManager:
    return _socket_manager


def get_scan_store() -> ScanStore:
    global _scan_store
    if _scan_store is None:
        settings = get_settings()
        if settings.database_url:
            from app.db.base import make_sessionmaker
            from app.services.postgres_scan_store import PostgresScanStore

            _scan_store = PostgresScanStore(make_sessionmaker(settings.database_url))
        else:
            _scan_store = InMemoryScanStore()
    return _scan_store


def get_identity_resolver() -> ObjectIdentityResolver:
    global _identity_resolver
    if _identity_resolver is None:
        settings = get_settings()
        _identity_resolver = ObjectIdentityResolver(
            match_distance_m=settings.id_match_distance_m,
            stale_sec=settings.id_stale_sec,
        )
    return _identity_resolver


def get_label_fusion() -> LabelFusion:
    return _label_fusion


def get_depth_estimator() -> DepthEstimator:
    global _depth_estimator
    if _depth_estimator is None:
        _depth_estimator = DepthEstimator(default_depth_m=get_settings().default_depth_m)
    return _depth_estimator


def init_background_services() -> None:
    settings = get_settings()
    queue = configure_gemini_queue(
        max_size=settings.gemini_queue_max_size,
        concurrency=settings.gemini_queue_concurrency,
        timeout_sec=settings.gemini_job_timeout_sec,
    )
    queue.start()


async def shutdown_background_services() -> None:
    await get_gemini_queue().stop()


def get_optional_gemini(api_key: Optional[str] = None) -> Optional[GeminiClient]:
    final_key = api_key or get_settings().gemini_api_key
    if not final_key:
        return None
    return GeminiClient(final_key)


def get_gemini_client(x_api_key: Optional[str] = Header(None)) -> GeminiClient:
    client = get_optional_gemini(x_api_key)
    if client is None:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header or GEMINI_API_KEY env var")
    return client

from typing import Optional

from fastapi import Header, HTTPException

from app.config import get_settings
from app.services.scan_store import InMemoryScanStore, ScanStore
from services.llm import GeminiClient
from services.socket_manager import ConnectionManager
from services.spatial_memory import SpatialMemory

_spatial_memory = SpatialMemory()
_socket_manager = ConnectionManager()
_scan_store: ScanStore = InMemoryScanStore()


def get_spatial_memory() -> SpatialMemory:
    return _spatial_memory


def get_socket_manager() -> ConnectionManager:
    return _socket_manager


def get_scan_store() -> ScanStore:
    return _scan_store


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

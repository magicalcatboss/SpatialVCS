import os
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import get_settings
from app.dependencies import get_spatial_memory
from services.video_processor import _get_yolo

router = APIRouter()


@router.get("/", response_model=dict[str, Any])
def health_check():
    spatial_memory = get_spatial_memory()
    settings = get_settings()
    return {
        "status": "online",
        "name": "SpatialVCS",
        "version": "2.1.0",
        "capabilities": {
            "search": spatial_memory.is_ready(),
            "yolo": _get_yolo() is not None,
            "gemini": settings.gemini_api_key is not None,
        },
    }


@router.get("/project_specification.md")
def get_project_specification():
    path = "project_specification.md"
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="project_specification.md not found")
    return FileResponse(path, media_type="text/markdown")


@router.get("/backend_capabilities.md")
def get_backend_capabilities():
    path = "backend_capabilities.md"
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="backend_capabilities.md not found")
    return FileResponse(path, media_type="text/markdown")

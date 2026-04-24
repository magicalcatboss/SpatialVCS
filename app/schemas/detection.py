from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.common import BoundingBox, Position3D


class Detection(BaseModel):
    object_key: str = ""
    label: str
    confidence: float = 0.0
    track_id: int = -1
    bbox: Optional[BoundingBox] = None
    position_3d: Position3D = Field(default_factory=Position3D)
    frame_path: str = ""
    gemini_name: Optional[str] = None
    gemini_details: Optional[str] = None


class DetectionRecord(BaseModel):
    object_key: str = ""
    label: str = ""
    yolo_label: str = ""
    gemini_name: str = ""
    confidence: float = 0.0
    position_3d: Position3D = Field(default_factory=Position3D)
    timestamp: float = 0.0
    frame_path: str = ""


class GeminiObject(BaseModel):
    object_key: str = ""
    name: str = ""
    position: Position3D | str = Field(default_factory=Position3D)
    details: str = ""
    bbox: Optional[BoundingBox] = None
    track_id: int = -1
    yolo_label: str = ""
    confidence: float = 0.0
    timestamp: Optional[float] = None
    frame_path: str = ""


class BroadcastObject(BaseModel):
    object_key: str = ""
    label: str = ""
    yolo_label: str = ""
    canonical_label: str = ""
    label_confidence: float = 0.0
    label_source: str = ""
    details: str = ""
    confidence: float = 0.0
    track_id: int = -1
    bbox: Optional[BoundingBox] = None
    position: Position3D = Field(default_factory=Position3D)


class StateVectorEntry(BaseModel):
    object_key: str = ""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    confidence: float = 0.0
    track_id: int = -1
    label: str = ""
    yolo_label: str = ""
    canonical_label: str = ""
    label_confidence: float = 0.0
    label_source: str = ""


class GeminiLabelCacheEntry(BaseModel):
    name: str = ""
    details: str = ""
    updated_at: float = 0.0

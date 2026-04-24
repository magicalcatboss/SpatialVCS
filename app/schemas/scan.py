from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.detection import DetectionRecord, GeminiLabelCacheEntry, GeminiObject


class ScanRecord(BaseModel):
    scan_id: str
    status: str = "scanning"
    source: Optional[str] = None
    frames: int = 0
    object_count: int = 0
    objects: list[GeminiObject] = Field(default_factory=list)
    detections: list[DetectionRecord] = Field(default_factory=list)
    gemini_label_cache: dict[str, GeminiLabelCacheEntry] = Field(default_factory=dict)
    last_frame_path: Optional[str] = None
    updated_at: Optional[float] = None


class ScanSummary(BaseModel):
    scan_id: str
    status: str = "unknown"
    source: Optional[str] = None
    frames: int = 0
    object_count: int = 0
    detection_count: int = 0
    updated_at: Optional[float] = None
    last_frame: str = ""


class ScanMemoryResponse(ScanRecord):
    pass


class ScansResponse(BaseModel):
    scans: list[ScanSummary] = Field(default_factory=list)

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Position3D
from app.schemas.scan import ScanMemoryResponse, ScanSummary


class SpatialQueryRequest(BaseModel):
    query: str
    scan_id: Optional[str] = None
    top_k: int = 3


class SpatialDiffRequest(BaseModel):
    scan_id_before: str
    scan_id_after: str
    threshold: float = 0.5


class SpatialQueryResult(BaseModel):
    score: float
    description: str
    frame_url: str
    yolo_data: list[dict[str, Any]] = Field(default_factory=list)
    position: Optional[Position3D] = None
    yolo_label: str = ""
    track_id: int = -1


class SpatialQueryResponse(BaseModel):
    query: str
    answer: Optional[str] = None
    results: list[SpatialQueryResult] = Field(default_factory=list)


class DiffEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    type: str
    label: str
    distance: Optional[float] = None
    from_: Optional[Position3D] = Field(default=None, alias="from")
    to: Optional[Position3D] = None


class SpatialDiffResponse(BaseModel):
    before_scan: str
    after_scan: str
    threshold: float
    change_count: int
    events: list[DiffEvent] = Field(default_factory=list)
    summary: str


class ProcessFrameResponse(BaseModel):
    status: str
    objects_found: int


class ResetResponse(BaseModel):
    status: str
    message: str

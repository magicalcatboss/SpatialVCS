from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field

from app.schemas.common import Pose
from app.schemas.detection import BroadcastObject, GeminiObject, StateVectorEntry


class AuthMessage(BaseModel):
    type: Literal["auth"]
    api_key: str


class StopScanMessage(BaseModel):
    type: Literal["stop_scan"]
    scan_id: str


class FrameMessage(BaseModel):
    type: Literal["frame"]
    image: str
    pose: Pose = Field(default_factory=Pose)
    scan_id: Optional[str] = None
    timestamp: Optional[float] = None
    api_key: Optional[str] = None


ProbeInboundMessage = Annotated[
    Union[AuthMessage, StopScanMessage, FrameMessage],
    Field(discriminator="type"),
]


class AckMessage(BaseModel):
    type: Literal["ack"]
    frame: int
    objects_found: int


class AuthAckMessage(BaseModel):
    type: Literal["auth_ack"]


class ErrorMessage(BaseModel):
    type: Literal["error"]
    message: str


class DetectionMessage(BaseModel):
    type: Literal["detection"]
    source: str
    scan_id: str
    frame_number: int
    objects: list[BroadcastObject]
    state_vector: dict[str, StateVectorEntry]
    gemini_objects: list[GeminiObject]
    pose: Pose
    timestamp: float
    log: str


class ScanCompletedMessage(BaseModel):
    type: Literal["scan_completed"]
    scan_id: str
    log: str


class ProbeDisconnectedMessage(BaseModel):
    type: Literal["probe_disconnected"]
    source: str


class SystemResetMessage(BaseModel):
    type: Literal["system_reset"]
    log: str


ProbeOutboundMessage = Annotated[
    Union[AckMessage, AuthAckMessage, ErrorMessage],
    Field(discriminator="type"),
]


DashboardOutboundMessage = Annotated[
    Union[DetectionMessage, ScanCompletedMessage, ProbeDisconnectedMessage, SystemResetMessage],
    Field(discriminator="type"),
]

import uuid

from sqlalchemy import BigInteger, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ObservationModel(Base):
    __tablename__ = "observations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    object_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("spatial_objects.id", ondelete="CASCADE"),
    )
    scan_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("scans.scan_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    track_id: Mapped[int] = mapped_column(Integer, default=-1)
    yolo_label: Mapped[str | None] = mapped_column(String)
    gemini_name: Mapped[str | None] = mapped_column(String)
    confidence: Mapped[float | None] = mapped_column(Float)
    bbox: Mapped[list | None] = mapped_column(JSONB)
    position_3d: Mapped[dict | None] = mapped_column(JSONB)
    pose: Mapped[dict | None] = mapped_column(JSONB)
    frame_path: Mapped[str | None] = mapped_column(String)
    timestamp: Mapped[float] = mapped_column(Float, nullable=False, index=True)

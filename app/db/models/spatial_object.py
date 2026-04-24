import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SpatialObjectModel(Base):
    __tablename__ = "spatial_objects"
    __table_args__ = (UniqueConstraint("scan_id", "object_key", name="idx_obj_scan_key"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("scans.scan_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    object_key: Mapped[str] = mapped_column(String, nullable=False)
    track_id: Mapped[int] = mapped_column(Integer, default=-1)
    canonical_label: Mapped[str] = mapped_column(String, nullable=False)
    yolo_label: Mapped[str | None] = mapped_column(String)
    gemini_name: Mapped[str | None] = mapped_column(String)
    gemini_details: Mapped[str | None] = mapped_column(String)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    last_position: Mapped[dict | None] = mapped_column(JSONB)
    last_bbox: Mapped[list | None] = mapped_column(JSONB)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

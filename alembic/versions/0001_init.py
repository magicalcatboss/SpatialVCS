"""Initialize SpatialVCS scan tables.

Revision ID: 0001_init
Revises:
Create Date: 2026-04-24
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "scans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("scan_id", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="scanning"),
        sa.Column("frame_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("object_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_frame_path", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("scan_id", name="uq_scans_scan_id"),
    )
    op.create_index("ix_scans_scan_id", "scans", ["scan_id"])
    op.create_index("idx_scans_status", "scans", ["status"])

    op.create_table(
        "spatial_objects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("scan_id", sa.Text(), sa.ForeignKey("scans.scan_id", ondelete="CASCADE"), nullable=False),
        sa.Column("object_key", sa.Text(), nullable=False),
        sa.Column("track_id", sa.Integer(), server_default="-1"),
        sa.Column("canonical_label", sa.Text(), nullable=False),
        sa.Column("yolo_label", sa.Text(), nullable=True),
        sa.Column("gemini_name", sa.Text(), nullable=True),
        sa.Column("gemini_details", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), server_default="0.0"),
        sa.Column("last_position", postgresql.JSONB(), nullable=True),
        sa.Column("last_bbox", postgresql.JSONB(), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("scan_id", "object_key", name="idx_obj_scan_key"),
    )
    op.create_index("idx_obj_scan", "spatial_objects", ["scan_id"])

    op.create_table(
        "observations",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("object_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("spatial_objects.id", ondelete="CASCADE"), nullable=True),
        sa.Column("scan_id", sa.Text(), sa.ForeignKey("scans.scan_id", ondelete="CASCADE"), nullable=False),
        sa.Column("track_id", sa.Integer(), server_default="-1"),
        sa.Column("yolo_label", sa.Text(), nullable=True),
        sa.Column("gemini_name", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("bbox", postgresql.JSONB(), nullable=True),
        sa.Column("position_3d", postgresql.JSONB(), nullable=True),
        sa.Column("pose", postgresql.JSONB(), nullable=True),
        sa.Column("frame_path", sa.Text(), nullable=True),
        sa.Column("timestamp", sa.Float(), nullable=False),
    )
    op.create_index("idx_obs_scan_ts", "observations", ["scan_id", "timestamp"])
    op.create_index("idx_obs_obj", "observations", ["object_id"])


def downgrade() -> None:
    op.drop_index("idx_obs_obj", table_name="observations")
    op.drop_index("idx_obs_scan_ts", table_name="observations")
    op.drop_table("observations")
    op.drop_index("idx_obj_scan", table_name="spatial_objects")
    op.drop_table("spatial_objects")
    op.drop_index("idx_scans_status", table_name="scans")
    op.drop_index("ix_scans_scan_id", table_name="scans")
    op.drop_table("scans")

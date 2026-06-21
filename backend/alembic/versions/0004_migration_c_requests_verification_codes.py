"""migration C: requests, verification_codes

Revision ID: 0004_migration_c
Revises: 0003_migration_b
Create Date: 2026-06-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0004_migration_c"
down_revision: Union[str, None] = "0003_migration_b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("prize_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "verification_pending",
                "placed",
                "confirmed",
                "rejected",
                "processing",
                "fulfilled",
                "cancelled",
                name="request_status",
                native_enum=False,
                length=30,
            ),
            nullable=False,
            server_default="placed",
        ),
        sa.Column("amount_rub", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("points_spent", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("inn", sa.String(length=12), nullable=False),
        sa.Column(
            "inn_verified_snapshot",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("knd_1122035_number_snapshot", sa.String(length=50), nullable=True),
        sa.Column(
            "self_employed_snapshot",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "phone_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("payout_phone", sa.String(length=20), nullable=True),
        sa.Column("payout_bank_account_snapshot", sa.String(length=100), nullable=True),
        sa.Column(
            "payout_details_changed_after_request",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "verification_method",
            sa.Enum(
                "sms",
                "email",
                name="verification_method",
                native_enum=False,
                length=10,
            ),
            nullable=True,
        ),
        sa.Column("verification_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("admin_comment", sa.Text(), nullable=True),
        sa.Column("fulfillment_data", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["prize_id"],
            ["prizes.id"],
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_requests_user_status", "requests", ["user_id", "status"])
    op.create_index("idx_requests_status", "requests", ["status"])
    op.create_index("ix_requests_user_id", "requests", ["user_id"])
    op.create_index("ix_requests_prize_id", "requests", ["prize_id"])

    op.create_table(
        "verification_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "target_type",
            sa.Enum(
                "profile_phone",
                "request_payout_phone",
                "other",
                name="verification_target_type",
                native_enum=False,
                length=30,
            ),
            nullable=False,
        ),
        sa.Column("target_value", sa.String(length=255), nullable=False),
        sa.Column(
            "method",
            sa.Enum(
                "sms",
                "email",
                name="verification_method",
                native_enum=False,
                length=10,
            ),
            nullable=False,
        ),
        sa.Column("code_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "attempts_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["requests.id"],
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_verification_codes_user_id", "verification_codes", ["user_id"])
    op.create_index(
        "ix_verification_codes_request_id",
        "verification_codes",
        ["request_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_verification_codes_request_id", table_name="verification_codes")
    op.drop_index("ix_verification_codes_user_id", table_name="verification_codes")
    op.drop_table("verification_codes")
    op.drop_index("ix_requests_prize_id", table_name="requests")
    op.drop_index("ix_requests_user_id", table_name="requests")
    op.drop_index("idx_requests_status", table_name="requests")
    op.drop_index("idx_requests_user_status", table_name="requests")
    op.drop_table("requests")

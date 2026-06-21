"""migration B: points_ledger, prizes, logs + seed SBP prize

Revision ID: 0003_migration_b
Revises: 0002_migration_a
Create Date: 2026-06-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0003_migration_b"
down_revision: Union[str, None] = "0002_migration_a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SYSTEM_SBP_PRIZE_ID = "a0000001-0000-4000-8000-000000000001"


def upgrade() -> None:
    op.create_table(
        "prizes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "type",
            sa.Enum(
                "certificate",
                "money",
                name="prize_type",
                native_enum=False,
                length=20,
            ),
            nullable=False,
            server_default="certificate",
        ),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("image_url", sa.String(length=500), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "points_ledger",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "active",
                "inactive",
                "redeemed",
                "pending_redemption",
                name="points_ledger_status",
                native_enum=False,
                length=30,
            ),
            nullable=False,
        ),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("period_month", sa.String(length=7), nullable=True),
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
            ["user_id"],
            ["users.id"],
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_points_user_status",
        "points_ledger",
        ["user_id", "status"],
    )
    op.create_index("idx_points_period", "points_ledger", ["period_month"])
    op.create_index("ix_points_ledger_user_id", "points_ledger", ["user_id"])

    op.create_table(
        "points_operations_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column(
            "operation_type",
            sa.Enum(
                "import",
                "activation",
                "reserve",
                "refund",
                "redeem",
                "manual_adjustment",
                name="points_operation_type",
                native_enum=False,
                length=30,
            ),
            nullable=False,
        ),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("admin_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["admin_id"],
            ["users.id"],
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
    op.create_index("ix_points_operations_log_user_id", "points_operations_log", ["user_id"])

    op.create_table(
        "points_overwritten_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("period_month", sa.String(length=7), nullable=False),
        sa.Column("old_amount", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("new_amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("old_status", sa.String(length=50), nullable=True),
        sa.Column("new_status", sa.String(length=50), nullable=False),
        sa.Column("import_file_name", sa.String(length=255), nullable=True),
        sa.Column("import_row_number", sa.Integer(), nullable=True),
        sa.Column("changed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["changed_by"],
            ["users.id"],
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
    op.create_index(
        "ix_points_overwritten_log_user_id",
        "points_overwritten_log",
        ["user_id"],
    )

    op.execute(
        sa.text(
            """
            INSERT INTO prizes (
                id, name, description, type, is_system, is_active, image_url,
                created_at, updated_at
            ) VALUES (
                :id,
                'Платеж на карту банка',
                NULL,
                'money',
                true,
                true,
                NULL,
                now(),
                now()
            )
            """
        ).bindparams(id=SYSTEM_SBP_PRIZE_ID)
    )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM prizes WHERE id = :id").bindparams(id=SYSTEM_SBP_PRIZE_ID)
    )
    op.drop_index("ix_points_overwritten_log_user_id", table_name="points_overwritten_log")
    op.drop_table("points_overwritten_log")
    op.drop_index("ix_points_operations_log_user_id", table_name="points_operations_log")
    op.drop_table("points_operations_log")
    op.drop_index("ix_points_ledger_user_id", table_name="points_ledger")
    op.drop_index("idx_points_period", table_name="points_ledger")
    op.drop_index("idx_points_user_status", table_name="points_ledger")
    op.drop_table("points_ledger")
    op.drop_table("prizes")

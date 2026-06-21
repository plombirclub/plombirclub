"""migration D: tasks, materials, products, parser_config

Revision ID: 0005_migration_d
Revises: 0004_migration_c
Create Date: 2026-06-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0005_migration_d"
down_revision: Union[str, None] = "0004_migration_c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("period_month", sa.String(length=7), nullable=False),
        sa.Column(
            "task_type",
            sa.Enum(
                "participation_conditions",
                "points_activation",
                name="task_type",
                native_enum=False,
                length=30,
            ),
            nullable=False,
        ),
        sa.Column(
            "source",
            sa.Enum(
                "system",
                "admin",
                name="task_source",
                native_enum=False,
                length=20,
            ),
            nullable=False,
            server_default="admin",
        ),
        sa.Column(
            "is_published",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            ondelete="SET NULL",
            onupdate="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tasks_created_by", "tasks", ["created_by"])
    op.create_index("ix_tasks_period_month", "tasks", ["period_month"])

    op.create_table(
        "task_distributors",
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("distributor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["distributor_id"],
            ["distributors.id"],
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["tasks.id"],
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        sa.PrimaryKeyConstraint("task_id", "distributor_id"),
        sa.UniqueConstraint("task_id", "distributor_id", name="uq_task_distributors_task_distributor"),
    )
    op.create_index("ix_task_distributors_distributor_id", "task_distributors", ["distributor_id"])

    op.create_table(
        "user_tasks_acceptance",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "accepted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["tasks.id"],
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
        sa.UniqueConstraint("user_id", "task_id", name="uq_user_tasks_acceptance_user_task"),
    )
    op.create_index("ix_user_tasks_acceptance_user_id", "user_tasks_acceptance", ["user_id"])
    op.create_index("ix_user_tasks_acceptance_task_id", "user_tasks_acceptance", ["task_id"])

    op.create_table(
        "materials",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "content_type",
            sa.Enum(
                "pdf",
                "pptx",
                "video",
                "image",
                "text",
                name="material_content_type",
                native_enum=False,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("file_path", sa.String(length=500), nullable=True),
        sa.Column("total_pages", sa.Integer(), nullable=True),
        sa.Column(
            "is_published",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
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
        "user_materials_progress",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("material_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "not_started",
                "started",
                "completed",
                name="material_progress_status",
                native_enum=False,
                length=20,
            ),
            nullable=False,
            server_default="not_started",
        ),
        sa.Column("pages_viewed", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("total_pages", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["material_id"],
            ["materials.id"],
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
        sa.UniqueConstraint(
            "user_id",
            "material_id",
            name="uq_user_materials_progress_user_material",
        ),
    )
    op.create_index("ix_user_materials_progress_user_id", "user_materials_progress", ["user_id"])
    op.create_index(
        "ix_user_materials_progress_material_id",
        "user_materials_progress",
        ["material_id"],
    )

    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("article", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.Column("category", sa.String(length=255), nullable=True),
        sa.Column("product_kind", sa.String(length=255), nullable=True),
        sa.Column("flavor", sa.String(length=255), nullable=True),
        sa.Column("composition", sa.Text(), nullable=True),
        sa.Column("weight_volume", sa.String(length=100), nullable=True),
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("product_group", sa.String(length=255), nullable=True),
        sa.Column("brand", sa.String(length=255), nullable=True),
        sa.Column("code", sa.String(length=100), nullable=True),
        sa.Column("unit_barcode", sa.String(length=50), nullable=True),
        sa.Column("box_barcode", sa.String(length=50), nullable=True),
        sa.Column("unit_volume", sa.String(length=50), nullable=True),
        sa.Column("net_weight", sa.String(length=50), nullable=True),
        sa.Column("pieces_per_box", sa.Integer(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "source",
            sa.Enum(
                "parser",
                "manual",
                name="product_source",
                native_enum=False,
                length=20,
            ),
            nullable=False,
            server_default="manual",
        ),
        sa.Column("manual_overrides", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
        sa.UniqueConstraint("article", name="uq_products_article"),
    )
    op.create_index("ix_products_article", "products", ["article"], unique=True)

    op.create_table(
        "product_distributors",
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("distributor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["distributor_id"],
            ["distributors.id"],
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        sa.PrimaryKeyConstraint("product_id", "distributor_id"),
        sa.UniqueConstraint(
            "product_id",
            "distributor_id",
            name="uq_product_distributors_product_distributor",
        ),
    )
    op.create_index(
        "ix_product_distributors_distributor_id",
        "product_distributors",
        ["distributor_id"],
    )

    op.create_table(
        "parser_config",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=False),
        sa.Column("selectors_config", sa.Text(), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["users.id"],
            ondelete="SET NULL",
            onupdate="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_parser_config_updated_by", "parser_config", ["updated_by"])


def downgrade() -> None:
    op.drop_index("ix_parser_config_updated_by", table_name="parser_config")
    op.drop_table("parser_config")
    op.drop_index("ix_product_distributors_distributor_id", table_name="product_distributors")
    op.drop_table("product_distributors")
    op.drop_index("ix_products_article", table_name="products")
    op.drop_table("products")
    op.drop_index("ix_user_materials_progress_material_id", table_name="user_materials_progress")
    op.drop_index("ix_user_materials_progress_user_id", table_name="user_materials_progress")
    op.drop_table("user_materials_progress")
    op.drop_table("materials")
    op.drop_index("ix_user_tasks_acceptance_task_id", table_name="user_tasks_acceptance")
    op.drop_index("ix_user_tasks_acceptance_user_id", table_name="user_tasks_acceptance")
    op.drop_table("user_tasks_acceptance")
    op.drop_index("ix_task_distributors_distributor_id", table_name="task_distributors")
    op.drop_table("task_distributors")
    op.drop_index("ix_tasks_period_month", table_name="tasks")
    op.drop_index("ix_tasks_created_by", table_name="tasks")
    op.drop_table("tasks")

"""add definition_suggestions and term_definitions tables

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-04-20 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("terms", "is_disputed")

    op.create_table(
        "definition_suggestions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("term_id", sa.Uuid(), nullable=False),
        sa.Column("definition", sa.String(2000), nullable=False),
        sa.Column("comment", sa.String(500), nullable=True),
        sa.Column("suggested_by", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["term_id"], ["terms.id"]),
        sa.ForeignKeyConstraint(["suggested_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_definition_suggestions_term_id", "definition_suggestions", ["term_id"])
    op.create_index(
        "ix_definition_suggestions_status", "definition_suggestions", ["status"]
    )

    op.create_table(
        "term_definitions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("term_id", sa.Uuid(), nullable=False),
        sa.Column("definition", sa.String(2000), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("added_by", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["term_id"], ["terms.id"]),
        sa.ForeignKeyConstraint(["added_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_term_definitions_term_id", "term_definitions", ["term_id"])


def downgrade() -> None:
    op.drop_index("ix_term_definitions_term_id", "term_definitions")
    op.drop_table("term_definitions")
    op.drop_index("ix_definition_suggestions_status", "definition_suggestions")
    op.drop_index("ix_definition_suggestions_term_id", "definition_suggestions")
    op.drop_table("definition_suggestions")
    op.add_column(
        "terms", sa.Column("is_disputed", sa.Boolean(), nullable=False, server_default="false")
    )

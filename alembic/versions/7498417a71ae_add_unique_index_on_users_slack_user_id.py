"""add unique index on users.slack_user_id

Revision ID: 7498417a71ae
Revises: 2277c37b0174
Create Date: 2026-04-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7498417a71ae'
down_revision: Union[str, None] = '2277c37b0174'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(op.f('ix_users_slack_user_id'), 'users', ['slack_user_id'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_users_slack_user_id'), table_name='users')

"""add level to job positions

Revision ID: 8e682f94c55d
Revises: 263963d3918b
Create Date: 2026-09-05 23:31:18.803621

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8e682f94c55d'
down_revision: Union[str, Sequence[str], None] = '263963d3918b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('job_positions', sa.Column('level', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('job_positions', 'level')

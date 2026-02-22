"""add word_deep_dives table

Revision ID: 0002
Revises: 0001
Create Date: 2026-02-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create word_deep_dives cache table."""
    op.create_table(
        'word_deep_dives',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('word', sa.String(length=255), nullable=False),
        sa.Column('response_json', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column('lookup_count', sa.Integer(), server_default='1', nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('word'),
    )
    op.create_index('idx_deep_dive_word', 'word_deep_dives', ['word'])


def downgrade() -> None:
    """Drop word_deep_dives table."""
    op.drop_index('idx_deep_dive_word', table_name='word_deep_dives')
    op.drop_table('word_deep_dives')

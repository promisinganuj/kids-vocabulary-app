"""add oauth columns to users table

Revision ID: 0003
Revises: 0002
Create Date: 2026-02-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0003'
down_revision: Union[str, Sequence[str], None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add OAuth provider columns and make password nullable for OAuth users."""
    op.add_column('users', sa.Column('oauth_provider', sa.String(50), nullable=True))
    op.add_column('users', sa.Column('oauth_id', sa.String(255), nullable=True))

    # Make password_hash and salt nullable so OAuth-only users can exist
    op.alter_column('users', 'password_hash', existing_type=sa.Text(), nullable=True)
    op.alter_column('users', 'salt', existing_type=sa.Text(), nullable=True)


def downgrade() -> None:
    """Remove OAuth columns and restore password NOT NULL constraints."""
    # Restore NOT NULL on password fields (fill NULLs first)
    bind = op.get_bind()
    bind.execute(sa.text(
        "UPDATE users SET password_hash = '', salt = '' "
        "WHERE password_hash IS NULL"
    ))

    op.alter_column('users', 'password_hash', existing_type=sa.Text(), nullable=False)
    op.alter_column('users', 'salt', existing_type=sa.Text(), nullable=False)

    op.drop_column('users', 'oauth_id')
    op.drop_column('users', 'oauth_provider')

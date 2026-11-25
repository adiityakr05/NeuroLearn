"""add started_at and actual_duration_minutes to study_sessions

Revision ID: c82e50f2bb23
Revises: b71d49e1fa12
Create Date: 2026-11-25 23:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c82e50f2bb23'
down_revision: Union[str, Sequence[str], None] = 'b71d49e1fa12'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('study_sessions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('started_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('actual_duration_minutes', sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('study_sessions', schema=None) as batch_op:
        batch_op.drop_column('actual_duration_minutes')
        batch_op.drop_column('started_at')

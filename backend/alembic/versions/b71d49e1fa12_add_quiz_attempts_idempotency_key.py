"""add idempotency_key to quiz_attempts

Revision ID: b71d49e1fa12
Revises: 8cb975f1ab35
Create Date: 2026-11-25 23:38:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b71d49e1fa12'
down_revision: Union[str, Sequence[str], None] = '8cb975f1ab35'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('quiz_attempts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('idempotency_key', sa.String(length=64), nullable=True))
        batch_op.create_index(batch_op.f('ix_quiz_attempts_idempotency_key'), ['idempotency_key'], unique=False)
        batch_op.create_unique_constraint('uq_user_quiz_idempotency', ['user_id', 'idempotency_key'])


def downgrade() -> None:
    with op.batch_alter_table('quiz_attempts', schema=None) as batch_op:
        batch_op.drop_constraint('uq_user_quiz_idempotency', type_='unique')
        batch_op.drop_index(batch_op.f('ix_quiz_attempts_idempotency_key'))
        batch_op.drop_column('idempotency_key')

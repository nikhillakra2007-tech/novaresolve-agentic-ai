"""add_replacement_quantity

Revision ID: 0002_add_replacement_quantity
Revises: 0001_initial_schema
Create Date: 2026-09-12 03:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0002_add_replacement_quantity'
down_revision: Union[str, None] = '0001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'replacements',
        sa.Column('quantity', sa.Integer(), server_default='1', nullable=False),
    )
    op.create_check_constraint(
        'chk_replacement_quantity_positive',
        'replacements',
        'quantity > 0',
    )


def downgrade() -> None:
    op.drop_constraint(
        'chk_replacement_quantity_positive',
        'replacements',
        type_='check',
    )
    op.drop_column('replacements', 'quantity')

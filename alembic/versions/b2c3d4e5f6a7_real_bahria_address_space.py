"""Widen sector for real block names; add plots.street

The grid moved from invented single-letter sectors to the society's real block names
("Overseas Enclave", "Abu Bakar Block", "Sector E-1"), which do not fit String(8).
plots.street carries the street the house sits on; it is informational, since house
numbers are unique within a block and the match key remains {phase, sector, house_ref}.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("plots", "sector", type_=sa.String(64), existing_type=sa.String(8))
    op.alter_column("listings", "sector", type_=sa.String(64), existing_type=sa.String(8))
    op.add_column("plots", sa.Column("street", sa.String(32), nullable=True))


def downgrade() -> None:
    # Truncation is unavoidable going back: real block names exceed 8 characters.
    op.drop_column("plots", "street")
    op.alter_column("listings", "sector", type_=sa.String(8), existing_type=sa.String(64))
    op.alter_column("plots", "sector", type_=sa.String(8), existing_type=sa.String(64))

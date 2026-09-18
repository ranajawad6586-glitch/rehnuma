"""Plots are claimed addresses, not a seeded register

Bahria Town's plot register is not public, so the app cannot pre-seed every plot or know a
possession reference or coordinates for one. Rows in `plots` are now created when an owner
claims a plausible address, so possession_ref and lat/lng become nullable.

The previously seeded synthetic grid is deleted: its street and house numbers were invented,
so it rejected real addresses while accepting fabricated ones. Listings that pointed at those
rows have their plot_id cleared rather than being deleted, so no owner loses a listing.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("plots", "possession_ref", nullable=True, existing_type=sa.String(64))
    op.alter_column("plots", "lat", nullable=True, existing_type=sa.Float())
    op.alter_column("plots", "lng", nullable=True, existing_type=sa.Float())
    # Drop the invented grid; keep the listings that referenced it.
    op.execute("UPDATE listings SET plot_id = NULL")
    op.execute("DELETE FROM plots")


def downgrade() -> None:
    # The synthetic grid is not recreated: it was wrong, and nothing should depend on it.
    op.execute("DELETE FROM plots")
    op.alter_column("plots", "lng", nullable=False, existing_type=sa.Float())
    op.alter_column("plots", "lat", nullable=False, existing_type=sa.Float())
    op.alter_column("plots", "possession_ref", nullable=False, existing_type=sa.String(64))

"""add listings.external_ref (for imported listings)

Revision ID: a1b2c3d4e5f6
Revises: 264304816de4
Create Date: 2026-06-01 19:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "264304816de4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("listings", sa.Column("external_ref", sa.String(length=255), nullable=True))
    op.create_index(op.f("ix_listings_external_ref"), "listings", ["external_ref"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_listings_external_ref"), table_name="listings")
    op.drop_column("listings", "external_ref")

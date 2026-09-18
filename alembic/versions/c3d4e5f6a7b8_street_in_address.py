"""Make street part of the address; sector optional

Phases 1-7 of Bahria Town have no block/sector layer — addresses are "House 123, Street 45,
Phase 4". Only Phase 8 is subdivided. So street becomes a required part of the address and of
the plot identity (house numbers restart on every street), while sector becomes an empty
string for phases without an area layer.

"" is used rather than NULL so the unique constraint keeps working: Postgres treats NULLs as
distinct, which would silently permit duplicate plots.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # plots.street exists (nullable) from the previous revision; make it a real column.
    op.execute("UPDATE plots SET street = '' WHERE street IS NULL")
    op.alter_column("plots", "street", nullable=False, server_default="")
    op.create_index("ix_plots_street", "plots", ["street"])

    op.drop_constraint("uq_plot_phase_sector_house", "plots", type_="unique")
    op.create_unique_constraint(
        "uq_plot_phase_sector_street_house", "plots",
        ["phase", "sector", "street", "house_ref"],
    )

    op.add_column("listings", sa.Column("street", sa.String(32), nullable=False,
                                        server_default=""))


def downgrade() -> None:
    op.drop_column("listings", "street")
    op.drop_constraint("uq_plot_phase_sector_street_house", "plots", type_="unique")
    op.create_unique_constraint("uq_plot_phase_sector_house", "plots",
                                ["phase", "sector", "house_ref"])
    op.drop_index("ix_plots_street", table_name="plots")
    op.alter_column("plots", "street", nullable=True, server_default=None)

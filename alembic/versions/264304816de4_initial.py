"""initial

Revision ID: 264304816de4
Revises: 
Create Date: 2026-06-01 18:50:23.994454
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '264304816de4'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('plots',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('phase', sa.String(length=16), nullable=False),
    sa.Column('sector', sa.String(length=8), nullable=False),
    sa.Column('house_ref', sa.String(length=32), nullable=False),
    sa.Column('possession_ref', sa.String(length=64), nullable=False),
    sa.Column('lat', sa.Float(), nullable=False),
    sa.Column('lng', sa.Float(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('phase', 'sector', 'house_ref', name='uq_plot_phase_sector_house')
    )
    op.create_index(op.f('ix_plots_house_ref'), 'plots', ['house_ref'], unique=False)
    op.create_index(op.f('ix_plots_phase'), 'plots', ['phase'], unique=False)
    op.create_index(op.f('ix_plots_sector'), 'plots', ['sector'], unique=False)
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=True),
    sa.Column('phone_hash', sa.String(length=64), nullable=False),
    sa.Column('cnic_hash', sa.String(length=64), nullable=True),
    sa.Column('phone', sa.String(length=255), nullable=True),
    sa.Column('can_own', sa.Boolean(), nullable=False),
    sa.Column('can_rent', sa.Boolean(), nullable=False),
    sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_cnic_hash'), 'users', ['cnic_hash'], unique=True)
    op.create_index(op.f('ix_users_phone_hash'), 'users', ['phone_hash'], unique=True)
    op.create_table('listings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('owner_id', sa.Integer(), nullable=False),
    sa.Column('plot_id', sa.Integer(), nullable=True),
    sa.Column('phase', sa.String(length=16), nullable=False),
    sa.Column('sector', sa.String(length=8), nullable=False),
    sa.Column('house_ref', sa.String(length=32), nullable=False),
    sa.Column('size', sa.String(length=16), nullable=False),
    sa.Column('rent', sa.Integer(), nullable=False),
    sa.Column('beds', sa.Integer(), nullable=False),
    sa.Column('baths', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('photos', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['plot_id'], ['plots.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_listings_owner_id'), 'listings', ['owner_id'], unique=False)
    op.create_index(op.f('ix_listings_plot_id'), 'listings', ['plot_id'], unique=False)
    op.create_index(op.f('ix_listings_status'), 'listings', ['status'], unique=False)
    op.create_table('ai_sessions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('listing_id', sa.Integer(), nullable=True),
    sa.Column('transcript', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('provider_used', sa.String(length=32), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['listing_id'], ['listings.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_sessions_listing_id'), 'ai_sessions', ['listing_id'], unique=False)
    op.create_index(op.f('ix_ai_sessions_user_id'), 'ai_sessions', ['user_id'], unique=False)
    op.create_table('deals',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('listing_id', sa.Integer(), nullable=False),
    sa.Column('tenant_id', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=24), nullable=False),
    sa.Column('locked_terms', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('tenant_consent_contact', sa.Boolean(), nullable=False),
    sa.Column('owner_consent_contact', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['listing_id'], ['listings.id'], ),
    sa.ForeignKeyConstraint(['tenant_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('listing_id', 'tenant_id', name='uq_deal_listing_tenant')
    )
    op.create_index(op.f('ix_deals_listing_id'), 'deals', ['listing_id'], unique=False)
    op.create_index(op.f('ix_deals_tenant_id'), 'deals', ['tenant_id'], unique=False)
    op.create_table('agreements',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('deal_id', sa.Integer(), nullable=False),
    sa.Column('terms', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('pdf_path', sa.String(length=255), nullable=True),
    sa.Column('stamp_duty_band', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['deal_id'], ['deals.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agreements_deal_id'), 'agreements', ['deal_id'], unique=True)
    op.create_table('messages',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('deal_id', sa.Integer(), nullable=False),
    sa.Column('sender_id', sa.Integer(), nullable=True),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('type', sa.String(length=16), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['deal_id'], ['deals.id'], ),
    sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_messages_deal_id'), 'messages', ['deal_id'], unique=False)
    op.create_table('offers',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('deal_id', sa.Integer(), nullable=False),
    sa.Column('sender_id', sa.Integer(), nullable=False),
    sa.Column('rent', sa.Integer(), nullable=False),
    sa.Column('advance_months', sa.Integer(), nullable=False),
    sa.Column('security', sa.Integer(), nullable=False),
    sa.Column('duration_months', sa.Integer(), nullable=False),
    sa.Column('move_in', sa.Date(), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['deal_id'], ['deals.id'], ),
    sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_offers_deal_id'), 'offers', ['deal_id'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_offers_deal_id'), table_name='offers')
    op.drop_table('offers')
    op.drop_index(op.f('ix_messages_deal_id'), table_name='messages')
    op.drop_table('messages')
    op.drop_index(op.f('ix_agreements_deal_id'), table_name='agreements')
    op.drop_table('agreements')
    op.drop_index(op.f('ix_deals_tenant_id'), table_name='deals')
    op.drop_index(op.f('ix_deals_listing_id'), table_name='deals')
    op.drop_table('deals')
    op.drop_index(op.f('ix_ai_sessions_user_id'), table_name='ai_sessions')
    op.drop_index(op.f('ix_ai_sessions_listing_id'), table_name='ai_sessions')
    op.drop_table('ai_sessions')
    op.drop_index(op.f('ix_listings_status'), table_name='listings')
    op.drop_index(op.f('ix_listings_plot_id'), table_name='listings')
    op.drop_index(op.f('ix_listings_owner_id'), table_name='listings')
    op.drop_table('listings')
    op.drop_index(op.f('ix_users_phone_hash'), table_name='users')
    op.drop_index(op.f('ix_users_cnic_hash'), table_name='users')
    op.drop_table('users')
    op.drop_index(op.f('ix_plots_sector'), table_name='plots')
    op.drop_index(op.f('ix_plots_phase'), table_name='plots')
    op.drop_index(op.f('ix_plots_house_ref'), table_name='plots')
    op.drop_table('plots')
    # ### end Alembic commands ###

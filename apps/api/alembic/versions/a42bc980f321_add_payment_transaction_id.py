"""Persist the provider-neutral payment transaction reference.

Revision ID: a42bc980f321
Revises: f3a91c07b2d4
"""
from alembic import op
import sqlalchemy as sa

revision = 'a42bc980f321'
down_revision = 'f3a91c07b2d4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('orders', sa.Column('payment_transaction_id', sa.String(length=255), nullable=True))
    op.execute(sa.text('UPDATE orders SET payment_transaction_id = stripe_payment_id WHERE stripe_payment_id IS NOT NULL'))


def downgrade() -> None:
    # Keep financial references rather than silently destroying reconciliation data.
    raise RuntimeError('Payment reference downgrade requires an explicit data retention plan')

"""Bind checkout requests and immutable payment initialization to one order."""
from alembic import op
import sqlalchemy as sa
revision = 'd74fe213c654'
down_revision = 'c63ed102b543'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('orders',sa.Column('checkout_request_id',sa.String(36),nullable=True))
    op.add_column('orders',sa.Column('checkout_fingerprint',sa.String(64),nullable=True))
    op.add_column('orders',sa.Column('checkout_data',sa.JSON(),nullable=True))
    op.add_column('orders',sa.Column('payment_setup_generation',sa.Integer(),nullable=False,server_default='0'))
    op.add_column('orders',sa.Column('payment_setup_lease_until',sa.DateTime(timezone=True),nullable=True))
    op.create_index('uq_orders_user_checkout_request','orders',['user_id','checkout_request_id'],unique=True)

def downgrade():
    raise RuntimeError('Checkout request and payment identity retention requires an explicit downgrade plan')

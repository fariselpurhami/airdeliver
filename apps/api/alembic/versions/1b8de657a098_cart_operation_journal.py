"""Prepare canonical cart and durable mutation identities, no runtime activation."""
from alembic import op
import sqlalchemy as sa
revision='1b8de657a098'
down_revision='0a7cd546f987'
branch_labels=None
depends_on=None


def upgrade():
    op.create_table('customer_cart_state',
        sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id'),primary_key=True),
        sa.Column('revision',sa.BigInteger(),nullable=False),
        sa.Column('state',sa.JSON(),nullable=False),
        sa.Column('changed_at',sa.DateTime(timezone=True),nullable=False))
    op.create_table('cart_mutation_record',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id'),nullable=False),
        sa.Column('mutation_id',sa.String(36),nullable=False),
        sa.Column('fingerprint',sa.String(64),nullable=False),
        sa.Column('revision',sa.BigInteger(),nullable=False),
        sa.Column('outcome',sa.JSON(),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint('user_id','mutation_id',name='uq_cart_mutation_customer_key'))
    op.create_index('ix_cart_mutation_record_user_id','cart_mutation_record',['user_id'])


def downgrade():
    raise RuntimeError('Cart journal rollback requires explicit data handling approval')

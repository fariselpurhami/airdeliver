"""Add opt-in customer shopping memory without altering legacy records."""
from alembic import op
import sqlalchemy as sa
revision='0a7cd546f987'
down_revision='f96bc435e876'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('customer_memory_consent',
        sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id'),primary_key=True),
        sa.Column('enabled',sa.Boolean(),nullable=False),
        sa.Column('policy_version',sa.String(32),nullable=False),
        sa.Column('changed_at',sa.DateTime(timezone=True),nullable=False))
    op.create_table('customer_shopping_memory',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id'),nullable=False),
        sa.Column('category',sa.String(32),nullable=False),
        sa.Column('value',sa.String(120),nullable=False),
        sa.Column('fingerprint',sa.String(64),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('expires_at',sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint('user_id','fingerprint',name='uq_customer_memory_fact'))
    op.create_index('ix_customer_shopping_memory_user_id','customer_shopping_memory',['user_id'])
    op.create_index('ix_customer_shopping_memory_expires_at','customer_shopping_memory',['expires_at'])

def downgrade():
    raise RuntimeError('Customer memory rollback requires explicit data handling approval')

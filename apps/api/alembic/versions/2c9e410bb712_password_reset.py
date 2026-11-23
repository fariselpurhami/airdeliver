"""Add reset credentials, audit and shared admission. Not owner-applied."""
from alembic import op
import sqlalchemy as sa
revision='2c9e410bb712'
down_revision='1b8de657a098'
branch_labels=None
depends_on=None

def upgrade():
    op.add_column('users',sa.Column('auth_version',sa.Integer(),nullable=False,server_default='0'))
    op.create_table('password_reset_tokens',sa.Column('token_hash',sa.String(64),primary_key=True),sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id'),nullable=False),sa.Column('expires_at',sa.DateTime(timezone=True),nullable=False),sa.Column('used_at',sa.DateTime(timezone=True)),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False))
    op.create_index('ix_password_reset_tokens_user_id','password_reset_tokens',['user_id'])
    op.create_table('password_reset_audits',sa.Column('id',sa.Integer(),primary_key=True),sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id')),sa.Column('event',sa.String(40),nullable=False),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False))
    op.create_index('ix_password_reset_audits_user_id','password_reset_audits',['user_id'])
    op.create_table('password_reset_admission',sa.Column('key_hash',sa.String(64),primary_key=True),sa.Column('window',sa.BigInteger(),nullable=False),sa.Column('count',sa.Integer(),nullable=False))

    op.create_table('password_reset_deliveries',sa.Column('id',sa.Integer(),primary_key=True),sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id'),nullable=False),sa.Column('encrypted_payload',sa.Text(),nullable=False),sa.Column('expires_at',sa.DateTime(timezone=True),nullable=False),sa.Column('sent_at',sa.DateTime(timezone=True)),sa.Column('attempts',sa.Integer(),nullable=False))
    op.create_index('ix_password_reset_deliveries_user_id','password_reset_deliveries',['user_id'])

def downgrade():
    raise RuntimeError('Explicit credential/audit data handling approval required')

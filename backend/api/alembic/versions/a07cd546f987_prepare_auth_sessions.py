"""Prepare refresh families. Do not apply outside specifically authorized DBs."""
from alembic import op
import sqlalchemy as sa

revision='a07cd546f987'
down_revision='1b8de657a098'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('auth_sessions',
        sa.Column('id',sa.String(64),primary_key=True),
        sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id'),nullable=False),
        sa.Column('expires_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('revoked_at',sa.DateTime(timezone=True),nullable=True))
    op.create_index('ix_auth_sessions_user_id','auth_sessions',['user_id'])
    op.create_table('refresh_credentials',
        sa.Column('digest',sa.String(64),primary_key=True),
        sa.Column('session_id',sa.String(64),sa.ForeignKey('auth_sessions.id'),nullable=False),
        sa.Column('used_at',sa.DateTime(timezone=True),nullable=True))
    op.create_index('ix_refresh_credentials_session_id','refresh_credentials',['session_id'])

def downgrade():
    raise RuntimeError('Session-history removal needs an explicit revocation/retention plan')

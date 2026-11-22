# apps/api/alembic/versions/f3a91c07b2d4_remove_drone_delivery.py
"""remove drone delivery feature

Drops the drone-delivery data model entirely: the missions table
(alembic-managed), the drones / drone_events / drone_telemetry tables
(present in deployments bootstrapped from schema.sql but never managed
by alembic), and the orders.drone_id / notifications.related_drone_id
columns.

Revision ID: f3a91c07b2d4
Revises: 2020ffde2651
"""
from alembic import op
import sqlalchemy as sa

revision = 'f3a91c07b2d4'
down_revision = '2020ffde2651'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index(op.f('ix_missions_status'), table_name='missions')
    op.drop_index(op.f('ix_missions_mission_id_str'), table_name='missions')
    op.drop_table('missions')

    op.drop_column('orders', 'drone_id')
    op.drop_column('notifications', 'related_drone_id')

    # Tables bootstrapped outside alembic (schema.sql); IF EXISTS keeps this
    # migration safe on databases that never had them.
    op.execute(sa.text('DROP TABLE IF EXISTS drone_events CASCADE'))
    op.execute(sa.text('DROP TABLE IF EXISTS drone_telemetry CASCADE'))
    op.execute(sa.text('DROP TABLE IF EXISTS drones CASCADE'))


def downgrade() -> None:
    op.add_column('orders', sa.Column('drone_id', sa.Integer(), nullable=True))
    op.add_column('notifications', sa.Column('related_drone_id', sa.Integer(), nullable=True))
    op.create_table(
        'missions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('mission_id_str', sa.String(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('waypoints', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('failure_reason', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_missions_mission_id_str'), 'missions', ['mission_id_str'], unique=True)
    op.create_index(op.f('ix_missions_status'), 'missions', ['status'], unique=False)
    # drones / drone_events / drone_telemetry are not recreated: alembic
    # never managed them, so there is no migration-owned shape to restore.

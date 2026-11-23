"""Add optional source provenance side tables, no catalog/order backfill.

Revision ID: 3da1f52cc823
Revises: 1b8de657a098
"""
from alembic import op
import sqlalchemy as sa
revision='3da1f52cc823'
down_revision='1b8de657a098'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('inventory_sources',sa.Column('id',sa.Integer(),primary_key=True),sa.Column('source_key',sa.String(100),nullable=False,unique=True),sa.Column('seller_key',sa.String(100),nullable=False),sa.Column('identity',sa.JSON(),nullable=False),sa.Column('terms',sa.JSON(),nullable=False),sa.Column('enabled',sa.Boolean(),nullable=False,server_default=sa.false()))
    op.create_index('ix_inventory_sources_seller_key','inventory_sources',['seller_key'])
    op.create_table('product_source_bindings',sa.Column('product_id',sa.Integer(),sa.ForeignKey('products.id'),primary_key=True),sa.Column('source_id',sa.Integer(),sa.ForeignKey('inventory_sources.id'),nullable=False),sa.Column('external_product_id',sa.String(255),nullable=False),sa.Column('external_variant_id',sa.String(255),nullable=False),sa.Column('origin_reference',sa.String(255),nullable=False),sa.Column('category',sa.String(50),nullable=False),sa.UniqueConstraint('source_id','external_variant_id','origin_reference',name='uq_source_variant_origin'))
    op.create_index('ix_product_source_bindings_source_id','product_source_bindings',['source_id'])
    op.create_table('order_line_source_snapshots',sa.Column('order_item_id',sa.Integer(),sa.ForeignKey('order_items.id'),primary_key=True),sa.Column('source_id',sa.Integer(),sa.ForeignKey('inventory_sources.id'),nullable=False),sa.Column('snapshot',sa.JSON(),nullable=False),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False))
    op.create_index('ix_order_line_source_snapshots_source_id','order_line_source_snapshots',['source_id'])
    # Stored provenance is append-only, including against accidental ORM edits.
    op.execute("CREATE FUNCTION prevent_source_snapshot_change() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Order line source snapshots are append-only'; END $$")
    op.execute('CREATE TRIGGER source_snapshot_immutable BEFORE UPDATE OR DELETE ON order_line_source_snapshots FOR EACH ROW EXECUTE FUNCTION prevent_source_snapshot_change()')

def downgrade():
    # Review backup/retention before using downgrade. Never run on owner DB automatically.
    op.execute('DROP TRIGGER source_snapshot_immutable ON order_line_source_snapshots')
    op.execute('DROP FUNCTION prevent_source_snapshot_change()')
    op.drop_table('order_line_source_snapshots')
    op.drop_table('product_source_bindings')
    op.drop_table('inventory_sources')

"""Persist explicit shipping snapshots and per-order currency."""
from alembic import op
import sqlalchemy as sa
revision = "c63ed102b543"
down_revision = "b52dc091a432"
branch_labels = None
depends_on = None


def upgrade():
    # Existing checkout historically charged USD. Do not invent a shipping
    # snapshot for historical orders whose address was never collected.
    op.add_column("orders", sa.Column("currency", sa.String(3), nullable=False, server_default="USD"))
    op.add_column("orders", sa.Column("shipping_address_data", sa.JSON(), nullable=True))


def downgrade():
    raise RuntimeError("Order currency/address retention requires an explicit downgrade plan")

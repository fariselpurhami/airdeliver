"""Add the durable payment event outbox.

Revision ID: b52dc091a432
Revises: a42bc980f321
"""
from alembic import op
import sqlalchemy as sa

revision = "b52dc091a432"
down_revision = "a42bc980f321"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payment_outbox",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("routing_key", sa.String(128), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(128), nullable=True),
        sa.UniqueConstraint("order_id", "kind", name="uq_payment_outbox_order_kind"),
    )
    op.create_index("ix_payment_outbox_order_id", "payment_outbox", ["order_id"])
    op.create_index("ix_payment_outbox_next_attempt_at", "payment_outbox", ["next_attempt_at"])
    op.create_index("ix_payment_outbox_delivered_at", "payment_outbox", ["delivered_at"])


def downgrade() -> None:
    raise RuntimeError("Payment event retention and pending delivery must be reconciled before downgrade")

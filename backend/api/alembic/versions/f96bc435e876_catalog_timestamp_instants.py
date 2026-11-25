"""Align catalog instants with the Product model without guessing legacy zones."""
import os
from zoneinfo import ZoneInfo
from alembic import context, op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'f96bc435e876'
down_revision = 'e85af324d765'
branch_labels = None
depends_on = None


def upgrade():
    supplied = context.get_x_argument(as_dictionary=True).get('legacy_timestamp_timezone') or os.getenv('LEGACY_TIMESTAMP_TIMEZONE')
    zone = supplied or 'UTC'
    ZoneInfo(zone)
    literal = str(sa.literal(zone).compile(dialect=postgresql.dialect(), compile_kwargs={'literal_binds': True}))
    for column in ('created_at', 'updated_at'):
        op.execute(sa.text(f"""
DO $migration$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.columns
             WHERE table_schema=current_schema() AND table_name='products'
             AND column_name='{column}' AND data_type='timestamp without time zone') THEN
    IF {'false' if supplied else 'true'} AND EXISTS (SELECT 1 FROM products WHERE "{column}" IS NOT NULL LIMIT 1) THEN
      RAISE EXCEPTION 'Populated product timestamps need explicit LEGACY_TIMESTAMP_TIMEZONE before migration';
    END IF;
    ALTER TABLE products ALTER COLUMN "{column}" TYPE TIMESTAMPTZ
      USING "{column}" AT TIME ZONE {literal};
  END IF;
END
$migration$;
"""))


def downgrade():
    raise RuntimeError('Converting catalog instants to naive timestamps requires an explicit retention plan')

"""Persist instants without host/session timezone shifts.

Existing naive timestamps require a verified LEGACY_TIMESTAMP_TIMEZONE or
-x legacy_timestamp_timezone=<IANA zone>. Empty tables need no such choice.
"""
import os
from zoneinfo import ZoneInfo
from alembic import context, op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision='e85af324d765'
down_revision='d74fe213c654'
branch_labels=None
depends_on=None

COLUMNS=(('users','created_at'),('users','updated_at'),('users','last_login'),
         ('orders','created_at'),('orders','updated_at'),('orders','paid_at'),
         ('user_activities','created_at'),('user_badges','awarded_at'),
         ('audit_trails','timestamp'),('ai_memory','last_updated'),('notifications','created_at'))


def upgrade():
    supplied=context.get_x_argument(as_dictionary=True).get('legacy_timestamp_timezone') or os.getenv('LEGACY_TIMESTAMP_TIMEZONE')
    zone=supplied or 'UTC'
    ZoneInfo(zone)  # Validate the operator's choice before emitting any DDL.
    literal=str(sa.literal(zone).compile(dialect=postgresql.dialect(),compile_kwargs={'literal_binds':True}))
    for table,column in COLUMNS:
        op.execute(sa.text(f"""
DO $migration$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.columns
             WHERE table_schema=current_schema() AND table_name='{table}'
               AND column_name='{column}' AND data_type='timestamp without time zone') THEN
    IF {'false' if supplied else 'true'} AND EXISTS (SELECT 1 FROM "{table}" WHERE "{column}" IS NOT NULL LIMIT 1) THEN
      RAISE EXCEPTION 'Populated legacy timestamps need explicit LEGACY_TIMESTAMP_TIMEZONE before migration';
    END IF;
    ALTER TABLE "{table}" ALTER COLUMN "{column}" TYPE TIMESTAMPTZ
      USING "{column}" AT TIME ZONE {literal};
  END IF;
END
$migration$;
"""))


def downgrade():
    raise RuntimeError('Converting financial instants back to naive timestamps requires an explicit retention plan')

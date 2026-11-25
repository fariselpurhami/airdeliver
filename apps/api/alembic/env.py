import asyncio
import os
import sys
import pkgutil
import importlib
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlmodel import SQLModel

# 💎 ARCHITECTURAL FIX: PATH INJECTION MUST HAPPEN BEFORE IMPORTS
# This tells Python where to find the 'app' module before trying to import it.
API_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if API_DIR not in sys.path:
    sys.path.append(API_DIR)

# Now we can safely import app modules
import app.models

models_package_path = os.path.dirname(app.models.__file__)
for _, module_name, _ in pkgutil.iter_modules([models_package_path]):
    if not module_name.startswith("_"):
        importlib.import_module(f"app.models.{module_name}")

config = context.config

if config.config_file_name is not None:
    # Migration helpers can run in an existing process. Never silence its
    # application diagnostics when Alembic configures its own loggers.
    fileConfig(config.config_file_name, disable_existing_loggers=False)

DATABASE_URL = os.getenv("DATABASE_URI")
if not DATABASE_URL:
    from app.core.config import get_core_settings
    DATABASE_URL = get_core_settings().DATABASE_URI

# ConfigParser treats percent signs as interpolation markers. URL-encoded
# credentials must survive unchanged when the engine reads this option.
config.set_main_option("sqlalchemy.url", DATABASE_URL.replace("%", "%%"))

target_metadata = SQLModel.metadata

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

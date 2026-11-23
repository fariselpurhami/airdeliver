"""Explicitly enabled mail worker. Never started implicitly by the API or tests.

Run after provider authorization/configuration only:
python -m app.commands.dispatch_password_resets
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from app.core.config import get_core_settings
from app.services.password_reset_service import delivery_ready,dispatch_pending

async def run():
    settings=get_core_settings()
    if not delivery_ready(settings):raise RuntimeError('Password-reset mail delivery is not configured')
    engine=create_async_engine(settings.DATABASE_URI)
    sessions=async_sessionmaker(engine,expire_on_commit=False)
    try:
        while True:
            async with sessions() as db:await dispatch_pending(db,settings)
            await asyncio.sleep(60)
    finally:await engine.dispose()

if __name__=='__main__':asyncio.run(run())

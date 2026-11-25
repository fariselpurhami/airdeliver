"""Bounded opt-in recovery of committed events. Never creates/captures payments.

Not started on API import/startup. Deployment enables a dedicated runner only
once delivery scope and consumer replay acceptance are verified. Concurrent
runners use existing row locks/skip_locked; transport remains at least once.
"""
import asyncio
import logging
from sqlalchemy import func,select
from app.models.payment_outbox import PaymentOutbox
from app.services.payment_outbox_service import dispatch_pending
logger=logging.getLogger('airdeliver.payment_outbox')

async def pending_summary(session_factory):
    async with session_factory() as db:
        from datetime import datetime,timezone
        now=datetime.now(timezone.utc)
        total=(await db.execute(select(func.count(PaymentOutbox.id)).where(PaymentOutbox.delivered_at.is_(None)))).scalar_one()
        due=(await db.execute(select(func.count(PaymentOutbox.id)).where(PaymentOutbox.delivered_at.is_(None),PaymentOutbox.next_attempt_at<=now))).scalar_one()
        return {'pending':total,'due':due}

async def reconcile_once(session_factory,broker,*,batch_size=20,deadline=30):
    if type(batch_size) is not int or not 1<=batch_size<=50:raise ValueError('batch_size must be1..50')
    if type(deadline) not in (int,float) or not 1<=deadline<=120:raise ValueError('deadline must be1..120seconds')
    async with session_factory() as db:
        try:
            async with asyncio.timeout(deadline):
                result=await dispatch_pending(db,broker,limit=batch_size)
            logger.info('payment_outbox_reconcile sent=%d failed=%d',result.sent,result.failed)
            return result
        except BaseException:
            await db.rollback()
            raise

async def run_reconciler(session_factory,broker,stop,*,interval=60,batch_size=20,deadline=30):
    if type(interval) not in (int,float) or not 5<=interval<=3600:raise ValueError('interval must be5..3600seconds')
    if type(batch_size) is not int or not 1<=batch_size<=50:raise ValueError('batch_size must be1..50')
    if type(deadline) not in (int,float) or not 1<=deadline<=120:raise ValueError('deadline must be1..120seconds')
    while not stop.is_set():
        try:
            await reconcile_once(session_factory,broker,batch_size=batch_size,deadline=deadline)
        except asyncio.CancelledError:raise
        except Exception as exc:
            # Fixed class metadata only, never event payload/customer text.
            logger.warning('payment_outbox_reconcile_failed error_type=%s',type(exc).__name__)
        try:await asyncio.wait_for(stop.wait(),timeout=interval)
        except TimeoutError:pass

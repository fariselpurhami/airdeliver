"""Default read-only counts; --dispatch explicitly enables broker publication.

Run from apps/api with configured deployment environment. This script never
contacts payment providers, captures, refunds, recreates events or applies DB
migrations. Do not enable delivery without consumer replay acceptance.
"""
import argparse,asyncio,json,signal
from app.services.payment_outbox_reconciler import pending_summary,reconcile_once,run_reconciler

def arguments():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--dispatch',action='store_true',help='Publish existing committed due events to configured broker')
 p.add_argument('--watch',action='store_true',help='Dedicated recurring runner; requires --dispatch')
 p.add_argument('--interval',type=int,default=60);p.add_argument('--batch-size',type=int,default=20)
 args=p.parse_args()
 if args.watch and not args.dispatch:p.error('--watch requires --dispatch')
 if not 5<=args.interval<=3600:p.error('--interval must be5..3600seconds')
 if not 1<=args.batch_size<=50:p.error('--batch-size must be1..50')
 return args

async def main(args):
 from app.db.session import AsyncSessionFactory,async_engine
 try:
  if not args.dispatch:
   print(json.dumps(await pending_summary(AsyncSessionFactory)));return
  from app.core.config import get_core_settings
  from app.services.rabbitmq_service import RabbitMQService
  broker=RabbitMQService(get_core_settings())
  try:
   await broker.connect()
   if args.watch:
    stop=asyncio.Event();loop=asyncio.get_running_loop()
    for sig in (signal.SIGINT,signal.SIGTERM):loop.add_signal_handler(sig,stop.set)
    await run_reconciler(AsyncSessionFactory,broker,stop,interval=args.interval,batch_size=args.batch_size)
   else:
    result=await reconcile_once(AsyncSessionFactory,broker,batch_size=args.batch_size)
    print(json.dumps({'sent':result.sent,'failed':result.failed}))
  finally:await broker.close()
 finally:await async_engine.dispose()

if __name__=='__main__':asyncio.run(main(arguments()))

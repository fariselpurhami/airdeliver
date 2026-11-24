"""One-shot owner-bound review of whole-cart lifecycle changes, no model mutation."""
from uuid import uuid4
from fastapi import HTTPException
from pydantic import BaseModel,ConfigDict,Field
from app.services.ai_cart_service import AICartService

class LifecycleConfirmation(BaseModel):
    model_config=ConfigDict(extra='forbid')
    review_id:str=Field(pattern=r'^[0-9a-f-]{36}$')

async def prepare(cache,user_id,operation):
    if operation not in {'clear','save'}:raise ValueError('Invalid lifecycle operation')
    service=AICartService(None,cache,None)
    cart=await service._get_cart_from_redis(user_id)
    if not cart.items:return None
    review_id=str(uuid4())
    await cache.set_json_required(f'cart_lifecycle_review:{user_id}:{review_id}',{'operation':operation,'snapshot':cart._snapshot},ttl=300)
    return {'review_id':review_id,'operation':operation,'item_count':len(cart.items)}

async def confirm(service,user_id,review_id):
    key=f'cart_lifecycle_review:{user_id}:{review_id}'
    record=await service.cache.get_json_required(key)
    if not record or record.get('operation') not in {'clear','save'}:raise HTTPException(409,'Review expired or already submitted. Refresh your cart.')
    # Consume before any effect. Uncertain completion must never auto-replay.
    if not await service.cache.compare_json_required(key,record,None,delete=True):raise HTTPException(409,'Review already submitted.')
    cart=await service._get_cart_from_redis(user_id)
    if cart._snapshot!=record['snapshot']:raise HTTPException(409,'Cart changed after review. Review it again.')
    if record['operation']=='clear':
        if not await service.cache.compare_json_required(service._get_cart_key(user_id),record['snapshot'],None,delete=True):raise HTTPException(409,'Cart changed during confirmation.')
        # Reviewed clear is deliberately cart-only. Never cancel pending orders.
        return {'status':'cleared'}
    return await service.handle_save_cart({'user_id':user_id,'expected_snapshot':record['snapshot']})

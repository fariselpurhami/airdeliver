"""Authenticated, self-only shopping-memory controls."""
from fastapi import APIRouter, Depends, HTTPException, Response
from app.services.cache_service import get_cache_from_request
from pydantic import BaseModel, ConfigDict, StrictBool
from sqlmodel.ext.asyncio.session import AsyncSession
from app.api import deps
from app.db.session import get_async_session
from app.models.user import User
from app.core.config import get_core_settings
from app.services.customer_memory_service import CustomerMemoryService, POLICY_VERSION, RETENTION_DAYS

router=APIRouter()


class MemoryConsentRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    enabled: StrictBool


@router.get('/memory')
async def export_memory(response: Response,current_user: User=Depends(deps.get_current_active_user), session: AsyncSession=Depends(get_async_session)):
    response.headers["Cache-Control"] = "no-store"
    return await CustomerMemoryService(session).export(current_user.id)


@router.put('/memory/consent')
async def update_memory_consent(body: MemoryConsentRequest,current_user: User=Depends(deps.get_current_active_user),session: AsyncSession=Depends(get_async_session),cache=Depends(get_cache_from_request)):
    if body.enabled and not get_core_settings().CUSTOMER_MEMORY_ENABLED:
        raise HTTPException(503,'Customer memory is not enabled in this environment')
    if body.enabled:
        from app.services.personalization_fence import key
        try:
            client=cache.client
            if client is not None and await client.exists(key(current_user.id)+':reset_pending'):
                raise HTTPException(409,'Finish personalization cleanup before enabling learning')
        except (AttributeError,NotImplementedError):pass
        except HTTPException:raise
        except Exception as exc:raise HTTPException(503,'Personalization cleanup status could not be checked') from exc
    await CustomerMemoryService(session).set_consent(current_user.id,body.enabled)
    return {'enabled':body.enabled,'policy_version':POLICY_VERSION,'retention_days':RETENTION_DAYS}


@router.delete('/memory')
async def delete_memory(current_user: User=Depends(deps.get_current_active_user),session: AsyncSession=Depends(get_async_session)):
    await CustomerMemoryService(session).erase_preferences(current_user.id)
    return {'enabled':False,'deleted':True,'scope':'Saved shopping preferences only, not order records or recent chat history'}


@router.delete('/memory/personalization')
async def delete_personalization(response: Response,current_user: User=Depends(deps.get_current_active_user),session: AsyncSession=Depends(get_async_session),cache=Depends(get_cache_from_request)):
    from app.services.personalization_erasure import PersonalizationErasure
    from app.services.ai_commerce_engine import get_milvus_client
    response.headers['Cache-Control']='no-store'
    try:
        import asyncio
        client=await asyncio.wait_for(asyncio.to_thread(get_milvus_client,get_core_settings()),15)
    except Exception:client=None
    try:result=await PersonalizationErasure(session,cache,client).erase(current_user.id)
    except Exception as exc:
        raise HTTPException(503,'Personalization erase could not be confirmed; retry before relying on it') from exc
    if not result['deleted']:response.status_code=503
    return result

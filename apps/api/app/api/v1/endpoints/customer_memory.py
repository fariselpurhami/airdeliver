"""Authenticated, self-only shopping-memory controls."""
from fastapi import APIRouter, Depends, HTTPException, Response
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
async def update_memory_consent(body: MemoryConsentRequest,current_user: User=Depends(deps.get_current_active_user),session: AsyncSession=Depends(get_async_session)):
    if body.enabled and not get_core_settings().CUSTOMER_MEMORY_ENABLED:
        raise HTTPException(503,'Customer memory is not enabled in this environment')
    await CustomerMemoryService(session).set_consent(current_user.id,body.enabled)
    return {'enabled':body.enabled,'policy_version':POLICY_VERSION,'retention_days':RETENTION_DAYS}


@router.delete('/memory')
async def delete_memory(current_user: User=Depends(deps.get_current_active_user),session: AsyncSession=Depends(get_async_session)):
    await CustomerMemoryService(session).erase_preferences(current_user.id)
    return {'enabled':False,'deleted':True,'scope':'Saved shopping preferences only, not order records or recent chat history'}

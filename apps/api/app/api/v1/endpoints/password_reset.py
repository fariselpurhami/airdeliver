import asyncio
import logging
import time
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.routing import APIRoute
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr
from sqlmodel.ext.asyncio.session import AsyncSession
from app.core.config import get_core_settings, CoreSettings
from app.core.limiter import limiter
from app.db.session import get_async_session
from app.services.password_reset_service import delivery_ready, issue_reset, consume_reset, send_reset_email, GENERIC_MESSAGE
class SecretSafeRoute(APIRoute):
    def get_route_handler(self):
        handler=super().get_route_handler()
        async def safe(request):
            try:return await handler(request)
            except RequestValidationError:
                return JSONResponse(status_code=422,content={'detail':'Invalid recovery input.'},headers={'Cache-Control':'no-store'})
        return safe
router=APIRouter(route_class=SecretSafeRoute)
logger=logging.getLogger(__name__)

class ResetRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    email: EmailStr

class ResetConfirm(BaseModel):
    model_config=ConfigDict(extra='forbid')
    token: SecretStr=Field(min_length=40,max_length=128)
    password: SecretStr=Field(min_length=8,max_length=128)

@router.post('/password-reset/request',status_code=202)
@limiter.limit('5/minute')
async def request_reset(request:Request,response:Response,data:ResetRequest,db:AsyncSession=Depends(get_async_session),settings:CoreSettings=Depends(get_core_settings)):
    response.headers['Cache-Control']='no-store'
    if not delivery_ready(settings):raise HTTPException(503,'Password recovery is temporarily unavailable. Please try again later.')
    started=time.monotonic()
    await issue_reset(db,str(data.email),request.client.host if request.client else 'unknown',settings)
    await asyncio.sleep(max(0,.35-(time.monotonic()-started)))
    return {'message':GENERIC_MESSAGE}

@router.post('/password-reset/confirm')
@limiter.limit('5/minute')
async def confirm_reset(request:Request,response:Response,data:ResetConfirm,db:AsyncSession=Depends(get_async_session),settings:CoreSettings=Depends(get_core_settings)):
    response.headers['Cache-Control']='no-store'
    if not settings.PASSWORD_RESET_ENABLED:raise HTTPException(503,'Password recovery is temporarily unavailable. Please try again later.')
    if not await consume_reset(db,data.token.get_secret_value(),data.password.get_secret_value()):raise HTTPException(400,'This reset link is invalid or expired. Request a new link.')
    response.delete_cookie('refresh_token',secure=settings.COOKIES_SECURE,httponly=True,samesite='lax')
    return {'message':'Password updated. Sign in again on each device.'}

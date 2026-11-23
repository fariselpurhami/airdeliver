import pytest
from fastapi import FastAPI
from httpx import AsyncClient,ASGITransport
from app.api.v1.endpoints.password_reset import router
from app.core.config import get_core_settings,settings
from app.core.limiter import limiter

@pytest.mark.asyncio
async def test_recovery_disabled_without_provider_fails_honestly():
 app=FastAPI();app.include_router(router)
 app.dependency_overrides[get_core_settings]=lambda:settings.model_copy(update={'PASSWORD_RESET_ENABLED':False})
 async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as client:
  response=await client.post('/password-reset/request',json={'email':'test@example.com'})
 assert response.status_code==503 and 'unavailable' in response.text

@pytest.mark.asyncio
async def test_validation_never_reflects_password_or_token():
 app=FastAPI();app.include_router(router)
 async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as client:
  response=await client.post('/password-reset/confirm',json={'token':'sensitive-short','password':'secret'})
 assert response.status_code==422
 assert 'secret' not in response.text and 'sensitive-short' not in response.text

def test_smtp_transport_requires_tls_and_does_not_print_secret(monkeypatch):
 from types import SimpleNamespace
 from pydantic import SecretStr
 from app.services.password_reset_service import send_reset_email
 import app.services.password_reset_service as module
 calls=[]
 class SMTP:
  def __init__(self,**kwargs):calls.append(('connect',kwargs))
  def __enter__(self):return self
  def __exit__(self,*args):pass
  def ehlo(self):calls.append(('ehlo',))
  def starttls(self,**kwargs):calls.append(('tls',kwargs))
  def login(self,*args):calls.append(('login',))
  def send_message(self,message):calls.append(('send',message))
 monkeypatch.setattr(module.smtplib,'SMTP',SMTP)
 cfg=settings.model_copy(update={'RESET_SMTP_STARTTLS':True,'RESET_SMTP_HOST':'fixture.test','RESET_SMTP_PORT':587,'RESET_SMTP_USERNAME':'fixture','RESET_SMTP_PASSWORD':SecretStr('not-real'),'RESET_EMAIL_FROM':'security@example.test'})
 send_reset_email('recipient@example.test','https://shop.example.test/reset-password#token=fixture',cfg)
 assert [x[0] for x in calls]==['connect','ehlo','tls','ehlo','login','send']
 assert calls[-1][1]['To']=='recipient@example.test'

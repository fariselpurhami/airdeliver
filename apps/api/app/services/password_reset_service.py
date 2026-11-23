"""Reset lifecycle: fixed origin, hashed credentials, row locks and shared quotas."""
import asyncio
import base64
import json
from cryptography.fernet import Fernet
import hashlib
import hmac
import secrets
import smtplib
import ssl
import time
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from urllib.parse import urlsplit
from sqlalchemy import update, case
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import select
from app.models.user import User
from app.models.password_reset import PasswordResetToken, PasswordResetAudit, PasswordResetAdmission, PasswordResetDelivery
from app.core.security import get_password_hash

GENERIC_MESSAGE = 'If an eligible account exists, a password reset link will be sent. Check your inbox and spam folder.'

def delivery_ready(settings):
    origin = urlsplit(settings.PASSWORD_RESET_WEB_ORIGIN or '')
    return bool(settings.PASSWORD_RESET_ENABLED and origin.scheme == 'https' and origin.netloc and not origin.username and not origin.password and origin.path in ('','/') and not origin.query and not origin.fragment and settings.RESET_SMTP_HOST and settings.RESET_EMAIL_FROM and settings.RESET_SMTP_USERNAME and settings.RESET_SMTP_PASSWORD)

def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()

def admission_key(value, settings):
    return hmac.new(settings.SECRET_KEY.get_secret_value().encode(),value.encode(),hashlib.sha256).hexdigest()

async def admit(db, key, limit, seconds, settings):
    now=int(time.time())//seconds
    table=PasswordResetAdmission.__table__
    stmt=insert(table).values(key_hash=admission_key(key,settings),window=now,count=1)
    stmt=stmt.on_conflict_do_update(index_elements=[table.c.key_hash],set_={'window':now,'count':case((table.c.window==now,table.c.count+1),else_=1)}).returning(table.c.count)
    return (await db.execute(stmt)).scalar_one()<=limit

async def issue_reset(db, email, ip, settings):
    # Quotas apply equally to present, absent and inactive accounts.
    ip_ok=await admit(db,'ip:'+ip,10,3600,settings)
    email_ok=await admit(db,'email:'+email.casefold(),3,3600,settings)
    if not ip_ok or not email_ok:
        await db.commit()
        return None
    user=(await db.execute(select(User).where(User.email==email).with_for_update())).scalars().first()
    now=datetime.now(timezone.utc)
    if not user or not user.is_active:
        await db.commit()
        return None
    await db.execute(update(PasswordResetToken).where(PasswordResetToken.user_id==user.id,PasswordResetToken.used_at.is_(None)).values(used_at=now))
    await db.execute(update(PasswordResetDelivery).where(PasswordResetDelivery.user_id==user.id,PasswordResetDelivery.sent_at.is_(None)).values(encrypted_payload='',sent_at=now))
    raw=secrets.token_urlsafe(32)
    db.add(PasswordResetToken(token_hash=token_hash(raw),user_id=user.id,expires_at=now+timedelta(minutes=settings.PASSWORD_RESET_TTL_MINUTES)))
    db.add(PasswordResetAudit(user_id=user.id,event='reset_requested'))
    link=settings.PASSWORD_RESET_WEB_ORIGIN.rstrip('/')+'/reset-password#token='+raw
    key=base64.urlsafe_b64encode(hmac.new(settings.SECRET_KEY.get_secret_value().encode(),b'airdeliver-reset-delivery-v1',hashlib.sha256).digest())
    encrypted=Fernet(key).encrypt(json.dumps({'recipient':user.email,'link':link}).encode()).decode()
    db.add(PasswordResetDelivery(user_id=user.id,encrypted_payload=encrypted,expires_at=now+timedelta(minutes=settings.PASSWORD_RESET_TTL_MINUTES)))
    await db.commit()
    # Fragment keeps token out of HTTP request targets, proxy logs and referrers.
    return user.email,settings.PASSWORD_RESET_WEB_ORIGIN.rstrip('/')+'/reset-password#token='+raw

async def consume_reset(db, raw, password):
    digest=token_hash(raw)
    candidate=await db.get(PasswordResetToken,digest)
    if not candidate:return False
    user=(await db.execute(select(User).where(User.id==candidate.user_id).with_for_update())).scalars().first()
    credential=(await db.execute(select(PasswordResetToken).where(PasswordResetToken.token_hash==digest).with_for_update().execution_options(populate_existing=True))).scalars().first()
    now=datetime.now(timezone.utc)
    if not user or not user.is_active or not credential or credential.used_at or credential.expires_at<=now:return False
    user.hashed_password=await asyncio.to_thread(get_password_hash,password)
    user.auth_version+=1
    await db.execute(update(PasswordResetToken).where(PasswordResetToken.user_id==user.id,PasswordResetToken.used_at.is_(None)).values(used_at=now))
    await db.execute(update(PasswordResetDelivery).where(PasswordResetDelivery.user_id==user.id,PasswordResetDelivery.sent_at.is_(None)).values(encrypted_payload='',sent_at=now))
    db.add(user);db.add(PasswordResetAudit(user_id=user.id,event='reset_completed'))
    await db.commit()
    return True

def send_reset_email(recipient, link, settings):
    message=EmailMessage()
    message['Subject']='Reset your airdeliver password'
    message['From']=settings.RESET_EMAIL_FROM
    message['To']=recipient
    message.set_content('A password reset was requested for your airdeliver account.\n\n'+link+'\n\nThis link expires in '+str(settings.PASSWORD_RESET_TTL_MINUTES)+' minutes and works once. If you did not request this, ignore this email. Your password has not changed.')
    context=ssl.create_default_context()
    cls=smtplib.SMTP if settings.RESET_SMTP_STARTTLS else smtplib.SMTP_SSL
    kwargs={'host':settings.RESET_SMTP_HOST,'port':settings.RESET_SMTP_PORT,'timeout':10}
    if not settings.RESET_SMTP_STARTTLS:kwargs['context']=context
    with cls(**kwargs) as client:
        if settings.RESET_SMTP_STARTTLS:client.ehlo();client.starttls(context=context);client.ehlo()
        client.login(settings.RESET_SMTP_USERNAME,settings.RESET_SMTP_PASSWORD.get_secret_value())
        client.send_message(message)


async def dispatch_pending(db, settings, sender=send_reset_email):
    """Bounded durable outbox batch, exclusive worker locks, at-least-once delivery."""
    if not delivery_ready(settings):return 0
    now=datetime.now(timezone.utc)
    await db.execute(update(PasswordResetDelivery).where(PasswordResetDelivery.expires_at<=now,PasswordResetDelivery.encrypted_payload!='').values(encrypted_payload=''))
    rows=(await db.execute(select(PasswordResetDelivery).where(PasswordResetDelivery.sent_at.is_(None),PasswordResetDelivery.expires_at>now,PasswordResetDelivery.attempts<5).order_by(PasswordResetDelivery.id).limit(10).with_for_update(skip_locked=True))).scalars().all()
    sent=0
    key=base64.urlsafe_b64encode(hmac.new(settings.SECRET_KEY.get_secret_value().encode(),b'airdeliver-reset-delivery-v1',hashlib.sha256).digest())
    for row in rows:
        row.attempts+=1
        try:
            payload=json.loads(Fernet(key).decrypt(row.encrypted_payload.encode()))
            await asyncio.to_thread(sender,payload['recipient'],payload['link'],settings)
        except Exception:
            db.add(PasswordResetAudit(user_id=row.user_id,event='delivery_failed'))
        else:
            row.sent_at=datetime.now(timezone.utc)
            row.encrypted_payload=''
            db.add(PasswordResetAudit(user_id=row.user_id,event='delivery_sent'));sent+=1
        db.add(row)
    await db.commit()
    return sent

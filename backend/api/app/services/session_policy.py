"""Transactional refresh-family policy, preparation only, not active auth.

Caller gives this service a dedicated AsyncSession. Successful policy commands
commit; cancellation and storage failures propagate and cannot mint credentials.
All commands lock user then family to serialize rotation/logout/disable together.
"""
import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime,timezone
from sqlmodel import select
from sqlalchemy import update
from app.models.user import User
from app.models.auth_session import AuthSession,RefreshCredential

class SessionRejected(ValueError):
    def __init__(self):super().__init__('session_rejected')

@dataclass(frozen=True)
class SessionCredential:
    session_id:str
    refresh_token:str
    expires_at:datetime

def digest(token):return hashlib.sha256(token.encode()).hexdigest()

class SessionPolicy:
    def __init__(self,db):self.db=db

    async def _user(self,uid):
        result=await self.db.execute(select(User).where(User.id==uid).with_for_update())
        return result.scalars().first()

    async def _family(self,uid,sid):
        result=await self.db.execute(select(AuthSession).where(AuthSession.id==sid,AuthSession.user_id==uid).with_for_update())
        return result.scalars().first()

    def _new(self,family):
        token=secrets.token_urlsafe(48)
        self.db.add(RefreshCredential(digest=digest(token),session_id=family.id))
        return SessionCredential(family.id,token,family.expires_at)

    async def issue(self,uid,expires_at):
        now=datetime.now(timezone.utc)
        if expires_at.tzinfo is None or expires_at<=now:raise SessionRejected()
        user=await self._user(uid)
        if user is None or not user.is_active:raise SessionRejected()
        family=AuthSession(id=secrets.token_urlsafe(32),user_id=uid,expires_at=expires_at)
        self.db.add(family);await self.db.flush()
        credential=self._new(family);await self.db.commit();return credential

    async def rotate(self,uid,sid,token):
        user=await self._user(uid)
        if user is None:raise SessionRejected()
        family=await self._family(uid,sid)
        now=datetime.now(timezone.utc)
        if family is None or family.revoked_at is not None or family.expires_at<=now:raise SessionRejected()
        if not user.is_active:
            await self._revoke_all(uid,now);await self.db.commit();raise SessionRejected()
        row=await self.db.get(RefreshCredential,digest(token))
        # A random/foreign token must not revoke a valid family (DoS boundary).
        if row is None or row.session_id!=sid:raise SessionRejected()
        if row.used_at is not None:
            family.revoked_at=now;self.db.add(family)
            # Commit replay revocation before reporting failure.
            await self.db.commit();raise SessionRejected()
        row.used_at=now;self.db.add(row)
        credential=self._new(family);await self.db.commit();return credential

    async def logout(self,uid,sid):
        user=await self._user(uid)
        if user is None:raise SessionRejected()
        family=await self._family(uid,sid)
        if family is None:raise SessionRejected()
        if family.revoked_at is None:family.revoked_at=datetime.now(timezone.utc);self.db.add(family)
        await self.db.commit()

    async def _revoke_all(self,uid,now):
        await self.db.execute(update(AuthSession).where(AuthSession.user_id==uid,AuthSession.revoked_at.is_(None)).values(revoked_at=now))

    async def disable(self,uid):
        user=await self._user(uid)
        if user is None:raise SessionRejected()
        user.is_active=False;self.db.add(user)
        await self._revoke_all(uid,datetime.now(timezone.utc));await self.db.commit()

    async def is_active(self,uid,sid):
        user=await self._user(uid)
        if user is None or not user.is_active:return False
        family=await self._family(uid,sid)
        return family is not None and family.revoked_at is None and family.expires_at>datetime.now(timezone.utc)

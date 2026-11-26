"""Offline fault boundaries supplement, never replace PostgreSQL concurrency tests."""
import asyncio
from datetime import datetime,timedelta,timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock,Mock
import pytest
from app.services.session_policy import SessionPolicy,SessionRejected

NOW=datetime.now(timezone.utc)


def policy():
 db=SimpleNamespace(execute=AsyncMock(),get=AsyncMock(),add=Mock(),flush=AsyncMock(),commit=AsyncMock())
 svc=SessionPolicy(db)
 svc._user=AsyncMock(return_value=SimpleNamespace(is_active=True))
 svc._family=AsyncMock(return_value=SimpleNamespace(id='family',revoked_at=None,expires_at=NOW+timedelta(hours=1)))
 return svc,db


@pytest.mark.asyncio
@pytest.mark.parametrize('error',[RuntimeError('store unavailable'),asyncio.CancelledError()])
@pytest.mark.parametrize('step',['flush','commit'])
async def test_issue_never_returns_a_credential_on_storage_failure_or_cancellation(error,step):
 svc,db=policy();getattr(db,step).side_effect=error
 with pytest.raises(type(error)):
  await svc.issue(1,NOW+timedelta(hours=1))
 if step=='flush':db.commit.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize('error',[RuntimeError('store unavailable'),asyncio.CancelledError()])
async def test_rotation_commit_failure_cannot_return_replacement(error):
 svc,db=policy();db.get.return_value=SimpleNamespace(session_id='family',used_at=None)
 db.commit.side_effect=error
 with pytest.raises(type(error)):await svc.rotate(1,'family','synthetic-token')
 db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_replay_commits_revocation_before_reporting_rejection():
 svc,db=policy();db.get.return_value=SimpleNamespace(session_id='family',used_at=NOW)
 with pytest.raises(SessionRejected):await svc.rotate(1,'family','synthetic-token')
 db.commit.assert_awaited_once()
 assert svc._family.return_value.revoked_at is not None


@pytest.mark.asyncio
async def test_replay_commit_outage_is_not_misreported_as_successful_revocation():
 svc,db=policy();db.get.return_value=SimpleNamespace(session_id='family',used_at=NOW)
 db.commit.side_effect=RuntimeError('store unavailable')
 with pytest.raises(RuntimeError):await svc.rotate(1,'family','synthetic-token')


@pytest.mark.asyncio
@pytest.mark.parametrize('row',[None,SimpleNamespace(session_id='other-family',used_at=NOW)])
async def test_unknown_or_foreign_refresh_never_commits_family_revocation(row):
 svc,db=policy();db.get.return_value=row
 with pytest.raises(SessionRejected):await svc.rotate(1,'family','synthetic-token')
 db.commit.assert_not_awaited();assert svc._family.return_value.revoked_at is None


@pytest.mark.asyncio
async def test_lock_lookup_cancellation_propagates_without_token_or_commit():
 svc,db=policy();svc._user.side_effect=asyncio.CancelledError()
 with pytest.raises(asyncio.CancelledError):await svc.rotate(1,'family','synthetic-token')
 db.get.assert_not_awaited();db.commit.assert_not_awaited()

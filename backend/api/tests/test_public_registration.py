from unittest.mock import AsyncMock
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.api.v1.endpoints import users
from app.models.enums import UserRole

@pytest.fixture
def registration(monkeypatch):
    db = SimpleNamespace(rollback=AsyncMock())
    app.dependency_overrides[users.get_async_session] = lambda: db
    lookup = AsyncMock(return_value=None)
    create = AsyncMock(return_value=SimpleNamespace(id=1, email='buyer@example.com', full_name='Buyer', role=UserRole.USER, is_active=True))
    monkeypatch.setattr(users.crud_user.user, 'get_by_email', lookup)
    monkeypatch.setattr(users.crud_user.user, 'create', create)
    yield TestClient(app), db, lookup, create
    app.dependency_overrides.clear()

BASE = {'email':'buyer@example.com', 'password':'valid-password', 'full_name':'Buyer'}

@pytest.mark.parametrize('extra', [{'role':'admin'}, {'is_active':False}, {'is_verified':True}])
def test_public_registration_rejects_privilege_fields(registration, extra):
    client, _, _, create = registration
    assert client.post('/api/v1/users/',json={**BASE, **extra}).status_code == 422
    create.assert_not_called()

@pytest.mark.parametrize('password',['short','x'*129])
def test_registration_password_bounds(registration,password):
    client, _, _, create=registration
    assert client.post('/api/v1/users/',json={**BASE,'password':password}).status_code == 422
    create.assert_not_called()

def test_registration_forces_server_owned_privileges(registration):
    client, _, _, create = registration
    assert client.post('/api/v1/users/',json=BASE).status_code == 201
    value = create.call_args.kwargs['obj_in']
    assert value.role == UserRole.USER and value.is_active

@pytest.mark.asyncio
async def test_crud_email_lookup_returns_scalar_user_not_row():
    import sqlalchemy as sa
    from sqlmodel import Session, select
    from app.models.user import User
    from app.crud.crud_user import CRUDUser
    from sqlalchemy.pool import StaticPool
    engine=sa.create_engine('sqlite://',poolclass=StaticPool)
    User.__table__.create(engine)
    with Session(engine) as session:
        user=User(email='buyer@example.com',hashed_password='test-only')
        session.add(user);session.commit()
        async def execute(statement): return session.execute(statement)
        result=await CRUDUser(User).get_by_email(SimpleNamespace(execute=execute),email='buyer@example.com')
        assert isinstance(result,User)
        assert result.email == 'buyer@example.com'
    engine.dispose()


def test_existing_account_is_not_recreated(registration):
    client, _, lookup, create = registration
    lookup.return_value = SimpleNamespace(id=1)
    assert client.post('/api/v1/users/',json=BASE).status_code == 400
    create.assert_not_called()


def test_duplicate_registration_race_rolls_back(registration):
    from sqlalchemy.exc import IntegrityError
    client, db, _, create = registration
    create.side_effect = IntegrityError('insert', {}, Exception('unique'))
    assert client.post('/api/v1/users/',json=BASE).status_code == 409
    db.rollback.assert_awaited_once()


def test_real_orm_registration_hashes_password_and_authenticates():
    import sqlalchemy as sa
    from sqlmodel import Session
    from sqlalchemy.pool import StaticPool
    from app.models.user import User
    from app.core.security import verify_password
    engine=sa.create_engine('sqlite://',poolclass=StaticPool,connect_args={'check_same_thread':False})
    User.__table__.create(engine)
    with Session(engine) as session:
        class Adapter:
            def add(self,value): session.add(value)
            async def execute(self,statement): return session.execute(statement)
            async def commit(self): session.commit()
            async def refresh(self,value): session.refresh(value)
            async def rollback(self): session.rollback()
        app.dependency_overrides[users.get_async_session] = lambda: Adapter()
        try:
            client=TestClient(app)
            response=client.post('/api/v1/users/',json={**BASE,'email':'real-orm@example.com'})
            assert response.status_code == 201, response.text
            stored=session.get(User,response.json()['id'])
            assert stored.role == UserRole.USER and stored.is_active
            assert stored.hashed_password != BASE['password']
            assert verify_password(BASE['password'],stored.hashed_password)
            token=client.post('/api/v1/auth/token',data={'username':'real-orm@example.com','password':BASE['password']})
            assert token.status_code == 200, token.text
            assert token.json()['access_token']
        finally:
            app.dependency_overrides.clear()
    engine.dispose()

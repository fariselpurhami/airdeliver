"""The startup seed must never replace or duplicate an existing catalog."""
from copy import deepcopy
from decimal import Decimal
from types import SimpleNamespace
import pytest
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlmodel import SQLModel, Session, create_engine, select
from app import models
from app.db.initial_data import seed_products, create_superuser
from app.models.enums import UserRole

@compiles(JSONB,'sqlite')
def sqlite_json_for_seed_tests(type_, compiler, **kwargs):
    return 'JSON'

@pytest.fixture
def database():
    engine=create_engine('sqlite://')
    SQLModel.metadata.create_all(engine,tables=[models.User.__table__,models.Product.__table__])
    with Session(engine) as session:
        yield session
    engine.dispose()


def test_seed_keeps_existing_product_and_only_adds_missing_sku(database):
    original=models.Product(sku='keep-existing',name='My existing fake product',description='preserve this',price=Decimal('29.50'),inventory=17)
    database.add(original); database.commit(); database.refresh(original)
    original_id=original.id
    incoming=[{'sku':'keep-existing','name':'Do not overwrite','description':'seed version','price':'1.00','inventory':1},
              {'sku':'add-new','name':'New seed product','description':'new','price':'4.00','inventory':5}]
    seed_products(database,deepcopy(incoming))
    seed_products(database,deepcopy(incoming))
    rows=database.exec(select(models.Product).order_by(models.Product.id)).all()
    assert len(rows)==2
    existing=next(p for p in rows if p.sku=='keep-existing')
    assert (existing.id,existing.name,existing.price,existing.inventory)==(original_id,'My existing fake product',Decimal('29.50'),17)


def test_superuser_bootstrap_is_idempotent_and_keeps_existing_password(database):
    settings=SimpleNamespace(FIRST_SUPERUSER='dev-admin@example.com',FIRST_SUPERUSER_PASSWORD='test-only-dev-password')
    create_superuser(database,settings)
    admin=database.exec(select(models.User)).one()
    old_hash=admin.hashed_password
    assert admin.role==UserRole.ADMIN
    settings.FIRST_SUPERUSER_PASSWORD='different-test-only-password'
    create_superuser(database,settings)
    assert len(database.exec(select(models.User)).all())==1
    assert database.exec(select(models.User)).one().hashed_password==old_hash

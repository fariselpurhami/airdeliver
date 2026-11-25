import os
from uuid import uuid4
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from app.models.user import User
from app.models.product import Product
from app.models.cart_journal import CustomerCartState
from app.services.cart_import_service import inspect_bundle,apply_bundle,bundle_digest,validate_bundle
from app.services.cart_journal_service import CartJournalConflict
pytestmark=pytest.mark.skipif(not os.getenv('TEST_POSTGRES_DSN'),reason='disposable PostgreSQL required')

@pytest.mark.asyncio
async def test_import_dryrun_replay_conflict_rollback_and_original_bundle_untouched():
 engine=create_async_engine(os.environ['TEST_POSTGRES_DSN']);sessions=async_sessionmaker(engine,expire_on_commit=False)
 async with sessions() as db:
  assert (await db.execute(text('select current_database()'))).scalar_one().startswith('airdeliver_test_')
  user=User(email=uuid4().hex+'@example.test',hashed_password='fixture');product=Product(sku=uuid4().hex,name='Fixture',description='',price='25.00',inventory=5)
  db.add_all([user,product]);await db.commit();uid,pid=user.id,product.id
 bundle={'version':1,'batch_id':str(uuid4()),'carts':[{'user_id':uid,'state':{'items':[{'product_id':pid,'name':'Fixture','price':'25.00','quantity':2}],'total':'999.00'}}]}
 digest=bundle_digest(bundle)
 async with sessions() as db:
  assert (await inspect_bundle(db,bundle))[0]['status']=='ready'
  assert await db.get(CustomerCartState,uid) is None
  with pytest.raises(ValueError):await apply_bundle(db,bundle,'wrong')
  await db.rollback()
  await apply_bundle(db,bundle,digest);await db.rollback()
  assert await db.get(CustomerCartState,uid) is None
  await apply_bundle(db,bundle,digest);await db.commit()
 async with sessions() as db:
  await apply_bundle(db,bundle,digest);await db.commit()
  row=await db.get(CustomerCartState,uid);assert row.revision==1 and row.state['total']=='50.00'
  newer={**bundle,'batch_id':str(uuid4())}
  with pytest.raises(CartJournalConflict):await apply_bundle(db,newer,bundle_digest(newer))
 assert bundle['carts'][0]['state']['total']=='999.00' and bundle_digest(bundle)==digest
 await engine.dispose()

def test_invalid_duplicate_owner_bundle_rejected():
 row={'user_id':1,'state':{'items':[]}}
 with pytest.raises(ValueError):validate_bundle({'version':1,'batch_id':str(uuid4()),'carts':[row,row]})


@pytest.mark.asyncio
async def test_invalid_owner_quarantines_entire_batch_no_partial_write():
 engine=create_async_engine(os.environ['TEST_POSTGRES_DSN']);sessions=async_sessionmaker(engine,expire_on_commit=False)
 async with sessions() as db:
  user=User(email=uuid4().hex+'@example.test',hashed_password='fixture');db.add(user);await db.commit();uid=user.id
  bundle={'version':1,'batch_id':str(uuid4()),'carts':[{'user_id':uid,'state':{'items':[]}},{'user_id':2147483647,'state':{'items':[]}}]}
  with pytest.raises(CartJournalConflict):await apply_bundle(db,bundle,bundle_digest(bundle))
  await db.rollback();assert await db.get(CustomerCartState,uid) is None
 await engine.dispose()

import os
import asyncio
from uuid import uuid4
from datetime import datetime,timezone,timedelta
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from app.models.user import User
from app.models.product import Product
from app.models.order import Order,OrderItem
from app.models.inventory_source import InventorySource,ProductSourceBinding,OrderLineSourceSnapshot
from app.services.inventory_source_service import snapshot_order_line,SourceUnavailable
from app.inventory_sources.contracts import SourceIdentity,SourceTerms,Operation
pytestmark=pytest.mark.skipif(not os.getenv('TEST_POSTGRES_DSN'),reason='disposable PostgreSQL required')

@pytest.mark.asyncio
async def test_two_sources_and_immutable_line_identity_without_changing_legacy_catalog():
 engine=create_async_engine(os.environ['TEST_POSTGRES_DSN']);sessions=async_sessionmaker(engine,expire_on_commit=False);now=datetime.now(timezone.utc)
 try:
  async with sessions() as db:
   user=User(email=uuid4().hex+'@example.test',hashed_password='fixture');db.add(user);await db.flush()
   order=Order(user_id=user.id,total_price=20);db.add(order);await db.flush()
   line_ids=[];source_ids=[]
   for kind in ('partner_merchant','airdeliver_own_stock'):
    key=uuid4().hex
    identity=SourceIdentity(source_key=key,seller_key=key,kind=kind,legal_seller_name='Fixture seller',seller_country='US',inventory_country='US')
    terms=SourceTerms(version='fixture-v1',approved=True,approval_reference='fixture-approval',effective_at=now-timedelta(days=1),expires_at=now+timedelta(days=1),allowed_categories=['clothing'],capabilities=[Operation.PLACE_ORDER],permitted_operations=[Operation.PLACE_ORDER],permits_airdeliver_checkout=True,permits_airdeliver_payment_collection=True,permits_airdeliver_branding=True)
    source=InventorySource(source_key=key,seller_key=key,identity=identity.model_dump(mode='json'),terms=terms.model_dump(mode='json'),enabled=True);db.add(source);await db.flush();source_ids.append(source.id)
    product=Product(sku=key,name='Fixture',description='Not an offer',price=10,inventory=5);db.add(product);await db.flush()
    db.add(ProductSourceBinding(product_id=product.id,source_id=source.id,external_product_id='p',external_variant_id='v',origin_reference='warehouse',category='clothing'))
    line=OrderItem(order_id=order.id,product_id=product.id,quantity=1,price_per_unit=10);db.add(line);await db.flush();line_ids.append(line.id)
   legacy=Product(sku=uuid4().hex,name='Legacy',description='Not an offer',price=10,inventory=5);db.add(legacy);await db.flush()
   legacy_line=OrderItem(order_id=order.id,product_id=legacy.id,quantity=1,price_per_unit=10);db.add(legacy_line);await db.commit();legacy_id=legacy_line.id
  async def attribute(line_id):
   async with sessions() as db:
    row=await snapshot_order_line(db,line_id,now=now);await db.commit();return row.order_item_id
  assert await asyncio.gather(attribute(line_ids[0]),attribute(line_ids[0]))==[line_ids[0],line_ids[0]]
  for line_id,kind in zip(line_ids,('partner_merchant','airdeliver_own_stock')):
   async with sessions() as db:
    snapshot=await snapshot_order_line(db,line_id,now=now);await db.commit()
    assert snapshot.snapshot['identity']['kind']==kind
   async with sessions() as db:
    source=await db.get(InventorySource,snapshot.source_id);source.identity={**source.identity,'legal_seller_name':'Changed future seller'};await db.commit()
   async with sessions() as db:
    repeat=await snapshot_order_line(db,line_id,now=now);assert repeat.snapshot['identity']['legal_seller_name']=='Fixture seller'
    assert repeat.order_item_id==snapshot.order_item_id
   async with sessions() as db:
    with pytest.raises(DBAPIError):
     await db.execute(text('UPDATE order_line_source_snapshots SET snapshot=\'{}\' WHERE order_item_id=:id'),{'id':line_id})
     await db.commit()
    await db.rollback()
  async with sessions() as db:
   with pytest.raises(SourceUnavailable,match='No verified inventory source'):await snapshot_order_line(db,legacy_id,now=now)
   await db.rollback()
   assert (await db.get(Product,legacy.id)).inventory==5
 finally:await engine.dispose()

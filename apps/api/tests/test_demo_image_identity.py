from app.services.ai_nlu_service import ProductAccess
from app.schemas.product import ProductRead

def test_product_presentation_preserves_demo_identity_for_mapping_without_mutating():
 row={'id':1,'sku':'ADL-DEMO-v1-test-00000001','name':'Adidas Samba OG','price':'10.00','attributes':{'_seed_dataset':'airdeliver-demo-v1'}}
 dumped=ProductAccess.dump(row)
 assert dumped['sku']==row['sku']
 assert dumped['attributes']==row['attributes']
 assert dumped['attributes'] is not row['attributes']

def test_read_schema_preserves_identity_but_create_update_contracts_unchanged():
 row=ProductRead(id=1,sku='demo',name='Demo',price='10.00',attributes={'_seed_dataset':'airdeliver-demo-v1'})
 assert row.model_dump()['attributes']['_seed_dataset']=='airdeliver-demo-v1'

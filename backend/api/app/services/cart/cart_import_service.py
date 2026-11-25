"""Offline import preparation, no runtime switch and no destructive rollback.

Operator must freeze ALL legacy writers and inspect the manifest first.
The original Redis namespace is never changed. Caller owns transactions.
"""
import hashlib
import json
from datetime import datetime,timezone
from uuid import UUID,uuid5
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import select
from app.models.cart_journal import CustomerCartState,CartMutationRecord
from app.models.user import User
from app.models.product import Product
from app.services.ai_cart_service import CartStateModel
from app.services.cart_journal_service import CartJournalService,CartJournalConflict

IMPORT_NAMESPACE=UUID('77ac24cf-65e1-4af7-93df-b0cf0604ced8')

def bundle_digest(bundle):
    return hashlib.sha256(json.dumps(bundle,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def validate_bundle(bundle):
    if not isinstance(bundle,dict) or set(bundle)!={'version','batch_id','carts'} or bundle['version']!=1:
        raise ValueError('Unsupported import bundle')
    batch=str(UUID(bundle['batch_id']))
    rows=bundle['carts']
    if not isinstance(rows,list) or len(rows)>10000:raise ValueError('Bounded carts array required')
    seen=set();normalized=[]
    for row in rows:
        if not isinstance(row,dict) or set(row)!={'user_id','state'}:raise ValueError('Invalid cart row')
        uid=row['user_id']
        if type(uid)is not int or not 0<uid<=2147483647 or uid in seen:raise ValueError('Invalid or duplicate owner')
        seen.add(uid)
        cart=CartStateModel.model_validate(row['state'])
        if len({line.product_id for line in cart.items})!=len(cart.items):raise ValueError('Duplicate cart product')
        from decimal import Decimal
        cart.total=sum((line.price*Decimal(line.quantity) for line in cart.items),Decimal('0.00'))
        normalized.append({'user_id':uid,'state':cart.model_dump(mode='json')})
    return batch,normalized

async def inspect_bundle(db,bundle):
    batch,rows=validate_bundle(bundle);report=[]
    for row in rows:
        uid=row['user_id'];identity=str(uuid5(IMPORT_NAMESPACE,batch+':'+str(uid)))
        user=await db.get(User,uid)
        status='ready'
        if user is None:status='missing_owner'
        for line in row['state']['items']:
            product=await db.get(Product,line['product_id'])
            if product is None or product.currency.upper()!='USD':status='invalid_product_or_currency'
        existing=await db.get(CustomerCartState,uid)
        receipt=(await db.execute(select(CartMutationRecord).where(CartMutationRecord.user_id==uid,CartMutationRecord.mutation_id==identity))).scalars().first()
        fingerprint=CartJournalService.fingerprint({'operation':'legacy_import','batch_id':batch,'state':row['state']})
        if existing is not None:
            status='already_imported' if receipt and receipt.fingerprint==fingerprint else 'existing_canonical_conflict'
        report.append({**row,'mutation_id':identity,'fingerprint':fingerprint,'status':status})
    return report

async def apply_bundle(db,bundle,expected_digest):
    if bundle_digest(bundle)!=expected_digest:raise ValueError('Import bundle digest changed')
    rows=await inspect_bundle(db,bundle)
    if any(row['status'] not in {'ready','already_imported'} for row in rows):raise CartJournalConflict('Import contains quarantined/conflicting rows')
    for row in rows:
        if row['status']=='already_imported':continue
        # Atomic insert-only, never overwrite existing canonical history, even
        # if another prepared process initialized it after the dry run.
        result=await db.execute(insert(CustomerCartState).values(user_id=row['user_id'],revision=1,state=row['state'],changed_at=datetime.now(timezone.utc)).on_conflict_do_nothing(index_elements=['user_id']).returning(CustomerCartState.user_id))
        if result.scalar_one_or_none() is None:raise CartJournalConflict('Canonical state changed after inspection')
        db.add(CartMutationRecord(user_id=row['user_id'],mutation_id=row['mutation_id'],fingerprint=row['fingerprint'],revision=1,outcome={'status':'imported','batch_id':bundle['batch_id'],'revision':1,'digest':expected_digest}))
    await db.flush()
    return {'status':'prepared_import_applied','rows':len(rows),'digest':expected_digest}

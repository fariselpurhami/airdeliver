"""Unwired preflight and immutable order-line attribution, no external effects."""
from datetime import datetime
from sqlalchemy import select
from app.models.order import OrderItem
from app.models.inventory_source import InventorySource,ProductSourceBinding,OrderLineSourceSnapshot
from app.inventory_sources.contracts import SourceIdentity,SourceTerms,Operation,operation_gate

class SourceUnavailable(ValueError):pass

async def snapshot_order_line(session, order_item_id: int, *, now: datetime) -> OrderLineSourceSnapshot:
    """Caller owns transaction and authenticated order/checkout authority.

    Locks line then binding/source. Must run before provider handoff in the future
    integrated workflow. Does not authorize payment or claim stock is reserved.
    Existing unattributed lines fail closed here, legacy checkout is not changed.
    """
    line=(await session.execute(select(OrderItem).where(OrderItem.id==order_item_id).with_for_update())).scalar_one_or_none()
    if line is None:raise SourceUnavailable('Order line unavailable')
    existing=await session.get(OrderLineSourceSnapshot,order_item_id)
    if existing is not None:
        if existing.snapshot.get('product_id')!=line.product_id or existing.snapshot.get('quantity')!=line.quantity:
            raise SourceUnavailable('Order line changed after source attribution')
        return existing
    binding=(await session.execute(select(ProductSourceBinding).where(ProductSourceBinding.product_id==line.product_id).with_for_update())).scalar_one_or_none()
    if binding is None:raise SourceUnavailable('No verified inventory source')
    source=(await session.execute(select(InventorySource).where(InventorySource.id==binding.source_id).with_for_update())).scalar_one()
    identity=SourceIdentity.model_validate(source.identity)
    terms=SourceTerms.model_validate(source.terms)
    if identity.source_key!=source.source_key or identity.seller_key!=source.seller_key:raise SourceUnavailable('Source identity mismatch')
    reasons=operation_gate(terms,Operation.PLACE_ORDER,binding.category,now=now)
    if not source.enabled or reasons:raise SourceUnavailable('Source is disabled or not permitted for checkout')
    row=OrderLineSourceSnapshot(order_item_id=line.id,source_id=source.id,snapshot={
        'identity':identity.model_dump(mode='json'),'terms':terms.model_dump(mode='json'),
        'external_product_id':binding.external_product_id,'external_variant_id':binding.external_variant_id,
        'origin_reference':binding.origin_reference,'category':binding.category,
        'product_id':line.product_id,'quantity':line.quantity,
    })
    session.add(row)
    await session.flush()
    return row

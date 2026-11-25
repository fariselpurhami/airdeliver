"""Durable cart checkpoint primitives. Not wired to customer traffic yet.

Caller owns commit/rollback. State plus receipt live in one PostgreSQL
transaction. Redis is deliberately absent: future caching is derived only.
"""
import json
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert
from sqlmodel import select
from app.models.cart_journal import CustomerCartState, CartMutationRecord


class CartJournalConflict(ValueError):
    pass


class CartJournalStale(ValueError):
    pass


class CartJournalService:
    def __init__(self, db):
        self.db = db

    @staticmethod
    def fingerprint(operation):
        return sha256(json.dumps(operation, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()

    async def locked_state(self, user_id):
        now=datetime.now(timezone.utc)
        await self.db.execute(insert(CustomerCartState).values(user_id=user_id,revision=0,
            state={'items':[],'total':'0.00'},changed_at=now).on_conflict_do_nothing(index_elements=['user_id']))
        return (await self.db.execute(select(CustomerCartState).where(CustomerCartState.user_id==user_id)
            .with_for_update().execution_options(populate_existing=True))).scalars().one()

    async def read_snapshot(self, user_id):
        """Read-only canonical envelope. Never imports or clears legacy Redis."""
        row=(await self.db.execute(select(CustomerCartState).where(
            CustomerCartState.user_id==user_id).execution_options(populate_existing=True))).scalars().one_or_none()
        if row is None:
            return None
        return {**deepcopy(row.state), 'revision':row.revision}

    async def apply_snapshot(self, user_id, mutation_id, operation, expected_revision, state):
        from app.services.ai_cart_service import CartStateModel
        identity=str(UUID(str(mutation_id)))
        fingerprint=self.fingerprint(operation)
        cart=await self.locked_state(user_id)
        receipt=(await self.db.execute(select(CartMutationRecord).where(
            CartMutationRecord.user_id==user_id,CartMutationRecord.mutation_id==identity))).scalars().one_or_none()
        if receipt:
            if receipt.fingerprint!=fingerprint:
                raise CartJournalConflict('Mutation key belongs to different operation data')
            return {'replayed':True,'outcome':deepcopy(receipt.outcome),
                'revision':cart.revision,'cart':deepcopy(cart.state)}
        if type(expected_revision) is not int or expected_revision!=cart.revision:
            raise CartJournalStale('Refresh canonical cart revision before retrying')
        validated=CartStateModel.model_validate(state)
        from decimal import Decimal
        validated.total=sum((line.price*Decimal(line.quantity) for line in validated.items),Decimal('0.00'))
        snapshot=validated.model_dump(mode='json')
        revision=cart.revision+1
        outcome={'status':'committed','revision':revision}
        cart.state=snapshot;cart.revision=revision;cart.changed_at=datetime.now(timezone.utc)
        self.db.add(cart)
        self.db.add(CartMutationRecord(user_id=user_id,mutation_id=identity,
            fingerprint=fingerprint,revision=revision,outcome=outcome))
        await self.db.flush()
        return {'replayed':False,'outcome':outcome,'revision':revision,'cart':deepcopy(snapshot)}

    async def mutate_product(self, user_id, mutation_id, operation, product_id, quantity, expected_revision):
        """Prepared add/remove using fresh catalog data; no inventory reservation."""
        from decimal import Decimal
        from app.models.product import Product
        from app.services.ai_cart_service import CartStateModel, CartItemModel
        if operation not in {'add','remove'}:
            raise ValueError('Unsupported cart operation')
        if type(product_id) is not int or not 0 < product_id <= 9223372036854775807:
            raise ValueError('Invalid product identifier')
        if type(quantity) is not int or not 1 <= quantity <= 99:
            raise ValueError('Invalid cart quantity')
        identity=str(UUID(str(mutation_id)))
        body={'operation':operation,'product_id':product_id,'quantity':quantity if operation=='add' else None,
            'expected_revision':expected_revision}
        fingerprint=self.fingerprint(body)
        row=await self.locked_state(user_id)
        receipt=(await self.db.execute(select(CartMutationRecord).where(
            CartMutationRecord.user_id==user_id,CartMutationRecord.mutation_id==identity))).scalars().one_or_none()
        if receipt:
            if receipt.fingerprint!=fingerprint:
                raise CartJournalConflict('Mutation key belongs to different operation data')
            return {'replayed':True,'outcome':deepcopy(receipt.outcome),'revision':row.revision,'cart':deepcopy(row.state)}
        if type(expected_revision) is not int or expected_revision!=row.revision:
            raise CartJournalStale('Refresh canonical cart revision before retrying')
        cart=CartStateModel.model_validate(row.state)
        if operation=='remove':
            cart.items=[line for line in cart.items if line.product_id!=product_id]
        else:
            product=await self.db.get(Product,product_id,populate_existing=True)
            if product is None or not product.is_active or product.inventory<=0:
                raise ValueError('Product unavailable or out of stock')
            if not isinstance(product.currency,str) or product.currency.upper()!='USD':
                raise ValueError('Product currency is unsupported by this USD cart')
            existing=next((line for line in cart.items if line.product_id==product_id),None)
            total_quantity=quantity+(existing.quantity if existing else 0)
            if total_quantity>99 or total_quantity>product.inventory:
                raise ValueError('Requested quantity unavailable')
            line=CartItemModel(product_id=product_id,name=product.name,quantity=total_quantity,
                price=Decimal(str(product.price)),image_url=getattr(product,'image_url','') or '',category=product.category or '')
            if existing:
                cart.items=[line if item.product_id==product_id else item for item in cart.items]
            else:
                cart.items.append(line)
        return await self.apply_snapshot(user_id,identity,body,expected_revision,cart.model_dump(mode='json'))

    async def clear_cart(self, user_id, mutation_id, expected_revision):
        """Prepared clear + existing pending-order cancellation in one SQL tx."""
        from app.models.order import Order
        from app.models.enums import OrderStatus
        operation={'operation':'clear_cart','expected_revision':expected_revision}
        result=await self.apply_snapshot(user_id,mutation_id,operation,expected_revision,{'items':[]})
        if result['replayed']:
            return result
        orders=(await self.db.execute(select(Order).where(
            Order.user_id==user_id,Order.status==OrderStatus.PENDING).with_for_update())).scalars().all()
        for order in orders:
            order.status=OrderStatus.CANCELLED
            self.db.add(order)
        await self.db.flush()
        return result

    async def save_list(self, user_id, mutation_id, expected_revision):
        """Create saved Order, empty canonical cart and receipt in ONE SQL tx.

        Prepared path only. No cache delete and no external call in transaction.
        """
        from decimal import Decimal
        from app.services.ai_cart_service import CartStateModel
        from app.models.order import Order, OrderItem
        from app.models.enums import OrderStatus, CancellationReason
        identity=str(UUID(str(mutation_id)))
        operation={'operation':'save_list','expected_revision':expected_revision}
        fingerprint=self.fingerprint(operation)
        cart=await self.locked_state(user_id)
        receipt=(await self.db.execute(select(CartMutationRecord).where(
            CartMutationRecord.user_id==user_id,CartMutationRecord.mutation_id==identity))).scalars().one_or_none()
        if receipt:
            if receipt.fingerprint!=fingerprint:
                raise CartJournalConflict('Mutation key belongs to different operation data')
            return {'replayed':True,'outcome':deepcopy(receipt.outcome),
                'revision':cart.revision,'cart':deepcopy(cart.state)}
        if type(expected_revision) is not int or expected_revision!=cart.revision:
            raise CartJournalStale('Refresh canonical cart before saving')
        validated=CartStateModel.model_validate(cart.state)
        if not validated.items:
            raise ValueError('Nothing to save')
        total=sum((line.price*Decimal(line.quantity) for line in validated.items),Decimal('0.00'))
        order=Order(user_id=user_id,status=OrderStatus.CANCELLED,
            cancellation_reason=CancellationReason.CHANGED_MIND,total_price=total,
            delivery_address='Saved List',created_at=datetime.now(timezone.utc))
        self.db.add(order);await self.db.flush()
        for line in validated.items:
            self.db.add(OrderItem(order_id=order.id,product_id=line.product_id,
                quantity=line.quantity,price_per_unit=line.price))
        revision=cart.revision+1
        outcome={'status':'saved','saved_order_id':order.id,'revision':revision}
        cart.state={'items':[],'total':'0.00'};cart.revision=revision;cart.changed_at=datetime.now(timezone.utc)
        self.db.add(cart)
        self.db.add(CartMutationRecord(user_id=user_id,mutation_id=identity,
            fingerprint=fingerprint,revision=revision,outcome=outcome))
        await self.db.flush()
        return {'replayed':False,'outcome':outcome,'revision':revision,'cart':deepcopy(cart.state)}

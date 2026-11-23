"""Read-only model sales follow-ups. Cart state is never mutated here."""
import logging
from decimal import Decimal
from sqlmodel import select
from app.models.product import Product
from app.services.complement_evidence import catalog_asserts_complement
from app.services.shopping_discovery import ShoppingBrief, catalog_result
from app.services.sales_response_service import SalesResponseRequest, SalesResponseService


class CartSalesService:
    def __init__(self, db, llm, *, timeout=12.0):
        self.db = db
        self.llm = llm
        self.timeout = timeout

    async def _current(self, anchor_id, candidates, operation, excluded):
        ids = list(dict.fromkeys([anchor_id] + [getattr(p, 'id', None) for p in candidates]))
        ids = [i for i in ids if type(i) is int and 0 < i <= 2147483647][:21]
        result = await self.db.execute(select(Product).where(Product.id.in_(ids)).execution_options(populate_existing=True))
        rows = {p.id: p for p in result.scalars().all()}
        anchor = rows.get(anchor_id)
        if anchor is None:
            return None, []
        anchor_card = catalog_result(anchor)
        if operation == 'added' and (anchor_card is None or anchor_card.stock_status != 'local_in_stock' or anchor_card.evidence_kind != 'local_catalog'):
            return None, []
        cards = []
        for identity in ids:
            row = rows.get(identity)
            if row is None or identity == anchor_id or identity in excluded:
                continue
            card = catalog_result(row)
            if card is None or card.stock_status != 'local_in_stock' or card.evidence_kind != 'local_catalog' or card.currency != 'USD' or card.price is None:
                continue
            if operation == 'added':
                ratio = Decimal('2') if Decimal(str(anchor.price)) < 50 else Decimal('.6')
                cap = Decimal(str(anchor.price)) * ratio if Decimal(str(anchor.price)) > 0 else Decimal('1000')
                if Decimal(card.price) > cap or not catalog_asserts_complement(anchor, row):
                    continue
            else:
                # Removed price is context, not the customer's maximum budget.
                # Preserve the engine's bounded alternative window and category.
                price = Decimal(str(anchor.price))
                if row.category != anchor.category or not (max(Decimal('0'), price * Decimal('.7') if price > 50 else Decimal('0')) <= Decimal(card.price) <= (price * Decimal('1.3') if price > 0 else Decimal('1000000'))):
                    continue
                card.relation = 'alternative'
            cards.append(card)
        return anchor, cards[:4]

    async def respond(self, *, anchor_id, candidates, operation, excluded):
        if operation not in {'added', 'removed'}:
            raise ValueError('Invalid cart follow-up operation')
        anchor, cards = await self._current(anchor_id, candidates, operation, excluded)
        if anchor is None or not cards or self.llm is None:
            logging.getLogger('airdeliver.cart_sales').info('cart_sales_skipped', extra={'operation': operation, 'candidate_count': len(cards), 'provider_adapter_present': self.llm is not None})
            return None
        before = [c.model_dump(mode='json') for c in cards]
        evidence = {
            'cart_event': operation,
            'sales_intent': 'CART_COMPLEMENTS' if operation == 'added' else 'CART_ALTERNATIVES',
            'relation': 'catalog_asserted_complement' if operation == 'added' else 'same_category_price_window',
            'compatibility_verified': False,
            'customer_preferences': 'unknown; do not infer removal reason, budget, tastes or language',
            'instruction_scope': 'Optional related-item advice only. No urgency, reservation or cart action claims. Do not claim a product is superior. Explain only listed facts. No customer language was recorded; use concise English.',
        }
        result = await SalesResponseService(self.llm.infer_sales_json, provider_ready=True, timeout=self.timeout).respond(
            SalesResponseRequest(message='Show optional related catalog items after a cart change.',
                products=tuple(cards), brief=ShoppingBrief(), mode='catalog_results',
                intent='CART_COMPLEMENTS' if operation == 'added' else 'CART_ALTERNATIVES', evidence=evidence))
        if result.response_kind == 'system_notice':
            # The operational cart confirmation already landed. Optional sales
            # failure is logged by the shared boundary, never fixed sales copy.
            return None
        _, fresh = await self._current(anchor_id, candidates, operation, excluded)
        if before != [c.model_dump(mode='json') for c in fresh]:
            logging.getLogger('airdeliver.cart_sales').info('cart_sales_evidence_changed', extra={'operation': operation})
            return None
        return result

"""Prepared canonical-SQL to derived-cache repair. Not traffic enabled.

This namespace is intentionally separate from legacy ai_cart keys. Cached data
never seeds SQL. SQL remains the read source even if cache repair is unavailable.
"""
from app.services.cart_journal_service import CartJournalService


class CartReconciliationService:
    KEY_PREFIX = 'canonical_cart:v1:'
    TTL = 86400

    def __init__(self, db, cache):
        self.db = db
        self.cache = cache

    async def reconcile(self, user_id):
        # Missing canonical row is NOT proof that an existing legacy cart is empty.
        source = await CartJournalService(self.db).read_snapshot(user_id)
        if source is None:
            return {'status': 'uninitialized', 'cart': None}
        key = f'{self.KEY_PREFIX}{user_id}'
        try:
            cached = await self.cache.get_json_required(key)
            if cached == source:
                return {'status': 'current', 'cart': source}
            # Never overwrite a potentially newer publication with an older SQL
            # read. Re-read on next reconcile; do not trust cache as source data.
            if isinstance(cached, dict) and type(cached.get('revision')) is int and cached['revision'] > source['revision']:
                return {'status': 'retry', 'cart': source}
            repaired = await self.cache.compare_json_required(key, cached, source, ttl=self.TTL)
            return {'status': 'repaired' if repaired else 'retry', 'cart': source}
        except Exception:
            # Outcome remains explicit, no success claim for failed/uncertain repair.
            return {'status': 'cache_unavailable', 'cart': source}

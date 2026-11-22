# apps/api/tests/test_ai_cart_service.py
"""Tests for AICartService: cart state machine + financial precision."""
import json
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.ai_cart_service import AICartService, CartStateModel


class FakeCache:
    def __init__(self, cart=None):
        self._cart = cart
        self.published = []
        self.deleted = []
        self.sets = []

    async def get_json(self, key):
        return self._cart

    async def set_json(self, key, value, ttl=None):
        self.sets.append((key, value, ttl))
        self._cart = value

    async def get_json_required(self,key):
        return await self.get_json(key)

    async def set_json_required(self,key,value,ttl=None):
        await self.set_json(key,value,ttl)

    async def delete_required(self,key):
        await self.delete(key)

    async def publish(self, channel, message):
        self.published.append((channel, json.loads(message)))

    async def delete(self, key):
        self.deleted.append(key)
        self._cart = None


class FakeDB:
    def __init__(self, product=None):
        self._product = product
        self.added = []
        self.commits = 0
        self.rollbacks = 0

    async def get(self, model, pk, **kwargs):
        return self._product

    def add(self, obj):
        self.added.append(obj)
        if getattr(obj, "id", None) is None:
            obj.id = 77

    async def flush(self):
        pass

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1


class FakeRabbit:
    async def publish(self, payload, routing_key):
        pass


def make_product(pid=7, name="Shoes", price=19.99):
    return SimpleNamespace(id=pid, name=name, price=price, image_url="img", category="footwear",is_active=True,inventory=100)


def make_service(cart=None, product=None):
    cache = FakeCache(cart)
    db = FakeDB(product)
    svc = AICartService(db=db, cache=cache, rabbitmq=FakeRabbit())
    return svc, cache, db


@pytest.mark.asyncio
async def test_sync_cart_pushes_state_even_when_empty():
    svc, cache, db = make_service()
    await svc.handle_sync_cart({"user_id": 1})
    previews = [p for _, p in cache.published if p.get("type") == "cart_preview"]
    assert previews, "UI must be hydrated even with an empty cart"
    assert previews[0]["content"]["items"] == []


@pytest.mark.asyncio
async def test_sync_cart_invalid_payload_is_dropped():
    svc, cache, db = make_service()
    await svc.handle_sync_cart({"user_id": "x"})
    assert not cache.published


@pytest.mark.asyncio
async def test_add_to_cart_creates_item_with_decimal_price():
    svc, cache, db = make_service(product=make_product())
    await svc.handle_add_to_cart({"user_id": 1, "product_id": 7, "quantity": 2})
    assert cache.sets, "cart must persist to redis"
    stored = cache.sets[-1][1]
    assert stored["items"][0]["product_id"] == 7
    assert stored["items"][0]["quantity"] == 2
    assert Decimal(stored["total"]) == Decimal("39.98")
    assert cache.sets[-1][2] == 86400  # deterministic TTL


@pytest.mark.asyncio
async def test_add_to_cart_increments_existing_item():
    existing = {
        "items": [{"product_id": 7, "name": "Shoes", "quantity": 1, "price": "19.99",
                   "image_url": "img", "category": "footwear"}],
        "total": "19.99",
    }
    svc, cache, db = make_service(cart=existing, product=make_product())
    await svc.handle_add_to_cart({"user_id": 1, "product_id": 7, "quantity": 3})
    stored = cache.sets[-1][1]
    assert len(stored["items"]) == 1
    assert stored["items"][0]["quantity"] == 4
    assert Decimal(stored["total"]) == Decimal("79.96")


@pytest.mark.asyncio
async def test_add_to_cart_missing_product_notifies_and_keeps_cart():
    svc, cache, db = make_service(product=None)
    await svc.handle_add_to_cart({"user_id": 1, "product_id": 999})
    assert not cache.sets
    errors = [p for _, p in cache.published if p.get("type") == "error"]
    assert errors


@pytest.mark.asyncio
async def test_add_to_cart_without_product_id_is_noop():
    svc, cache, db = make_service(product=make_product())
    await svc.handle_add_to_cart({"user_id": 1})
    assert not cache.sets and not cache.published


@pytest.mark.asyncio
async def test_corrupt_cart_state_is_not_reported_as_empty():
    svc, cache, db = make_service(cart={"items": [{"bogus": True}]})
    from app.services.ai_cart_service import CartPersistenceError
    with pytest.raises(CartPersistenceError):
        await svc.handle_sync_cart({"user_id": 1})
    assert not cache.published


@pytest.mark.asyncio
async def test_save_cart_empty_is_error():
    svc, cache, db = make_service()
    await svc.handle_save_cart({"user_id": 1})
    assert not db.added
    errors = [p for _, p in cache.published if p.get("type") == "error"]
    assert errors


@pytest.mark.asyncio
async def test_save_cart_persists_order_and_clears_cart():
    cart = {
        "items": [{"product_id": 7, "name": "Shoes", "quantity": 2, "price": "19.99",
                   "image_url": "img", "category": "footwear"}],
        "total": "39.98",
    }
    svc, cache, db = make_service(cart=cart)
    await svc.handle_save_cart({"user_id": 1})
    assert db.commits == 1
    assert cache.deleted, "cart key must be evicted after save"
    previews = [p for _, p in cache.published if p.get("type") == "cart_preview"]
    assert previews[-1]["content"]["items"] == [], "UI receives the cleared cart"


@pytest.mark.asyncio
async def test_financial_total_uses_exact_decimal_math():
    # 0.1 + 0.2 style floats must not leak phantom cents
    existing = {
        "items": [
            {"product_id": 1, "name": "A", "quantity": 1, "price": "0.10", "image_url": "", "category": ""},
            {"product_id": 2, "name": "B", "quantity": 1, "price": "0.20", "image_url": "", "category": ""},
        ],
        "total": "0.30",
    }
    svc, cache, db = make_service(cart=existing, product=make_product(pid=3, name="C", price=0.30))
    await svc.handle_add_to_cart({"user_id": 1, "product_id": 3, "quantity": 1})
    stored = cache.sets[-1][1]
    assert Decimal(stored["total"]) == Decimal("0.60")


@pytest.mark.asyncio
@pytest.mark.parametrize('bad', [0,-1,100,True,1.5,'1.5'])
async def test_internal_cart_command_rejects_invalid_quantity_without_cache_write(bad):
    svc,cache,db=make_service(product=make_product())
    await svc.handle_add_to_cart({'user_id':1,'product_id':7,'quantity':bad})
    assert not cache.sets


@pytest.mark.asyncio
@pytest.mark.parametrize('field,bad', [('user_id',0),('user_id',-1),('user_id',True),('product_id',-1),('product_id',True),('product_id',2**64)])
async def test_internal_cart_command_rejects_invalid_owner_product_ids(field,bad):
    svc,cache,db=make_service(product=make_product())
    await svc.handle_add_to_cart({**{'user_id':1,'product_id':7},field:bad})
    assert not cache.sets

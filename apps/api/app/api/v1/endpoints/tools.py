# apps/api/app/api/v1/endpoints/tools.py

from app.models.product import Product
from fastapi import APIRouter, Depends, Query
from app.api import deps
from app.db.session import get_session
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List, Dict, Any
import random

router = APIRouter()

FAKE_INVENTORY_DB = {
    "sku_iphone_17_128": {"available_qty": 15, "reserved_qty": 2},
    "sku_case_leather_blk": {"available_qty": 50, "reserved_qty": 5},
}
FAKE_CARTS_DB = {}
FAKE_USER_MEMORY_DB = {
    "1": {
        "preferred_brands": ["Apple"],
        "address_book": [{"label": "home", "address": "El-Gesh Street, Cairo"}],
        "language_pref": "en",
    }
}


@router.get("/PRODUCT_SEARCH")
async def product_search(
    query: str = Query(..., description="Product name to search for"),
    session: AsyncSession = Depends(get_session),
):
    search_query = f"%{query.lower()}%"

    statement = select(Product).where(Product.name.ilike(search_query))
    result = await session.exec(statement)
    products = result.all()

    if not products:
        return []

    return [
        {
            "sku": f"sku_{p.name.lower().replace(' ', '_')}_{p.id}",
            "title": p.name,
            "price": float(p.price),
            "stock": p.inventory or 0,
            "eta_estimate_mins": random.randint(10, 20),
            "rating": round(random.uniform(4.5, 5.0), 1),
            "image_url": f"/images/{p.image_url}"
            if p.image_url
            else "/images/default.jpeg",
        }
        for p in products
    ]


@router.get("/INVENTORY_CHECK")
def inventory_check(sku: str) -> dict:
    """Simulates checking the live inventory for a specific SKU."""
    print(f"--- TOOL CALLED: INVENTORY_CHECK for SKU: '{sku}' ---")
    return FAKE_INVENTORY_DB.get(sku, {"available_qty": 0, "reserved_qty": 0})


@router.get("/CART_GET")
def cart_get(userId: str) -> dict:
    """Simulates getting a user's current cart."""
    print(f"--- TOOL CALLED: CART_GET for user: '{userId}' ---")
    return FAKE_CARTS_DB.get(userId, {"cartId": f"c_{userId}", "items": [], "total": 0.0})


@router.post("/CART_ADD")
def cart_add(userId: str, sku: str, qty: int, price: float = 1199.99) -> dict:
    """Simulates adding an item to the cart and returning a snapshot."""
    print(f"--- TOOL CALLED: CART_ADD for user '{userId}' with SKU '{sku}' ---")
    cart = FAKE_CARTS_DB.get(
        userId, {"cartId": f"c_{userId}", "items": [], "total": 0.0}
    )

    found = False
    for item in cart["items"]:
        if item["sku"] == sku:
            item["qty"] += qty
            found = True
            break
    if not found:
        cart["items"].append({"sku": sku, "qty": qty, "price": price})

    cart["total"] = sum(i["price"] * i["qty"] for i in cart["items"])
    FAKE_CARTS_DB[userId] = cart
    return cart


@router.post("/CART_REMOVE")
def cart_remove(userId: str, sku: str, qty: int) -> dict:
    """Simulates removing an item from the cart."""
    print(f"--- TOOL CALLED: CART_REMOVE for user '{userId}' with SKU '{sku}' ---")
    cart = FAKE_CARTS_DB.get(
        userId, {"cartId": f"c_{userId}", "items": [], "total": 0.0}
    )
    cart["items"] = [item for item in cart["items"] if item["sku"] != sku]
    cart["total"] = sum(i["price"] * i["qty"] for i in cart["items"])
    FAKE_CARTS_DB[userId] = cart
    return cart


@router.post("/ORDER_CREATE")
def order_create(userId: str, cartId: str, paymentMethod: str) -> dict:
    """Simulates creating an order from a cart."""
    print(f"--- TOOL CALLED: ORDER_CREATE for cart: '{cartId}' ---")
    cart = FAKE_CARTS_DB.pop(userId, None)
    if not cart:
        return {"status": "error", "message": "Cart not found."}
    order_id = f"ord_{random.randint(1000, 9999)}"
    return {
        "orderId": order_id,
        "status": "processing",
        "eta_mins": 14,
        "tracking_url": f"/tracking/{order_id}",
    }


@router.get("/ORDER_TRACK")
def order_track(orderId: str) -> dict:
    """Simulates tracking an order."""
    print(f"--- TOOL CALLED: ORDER_TRACK for order '{orderId}' ---")
    return {
        "status": "in_transit",
        "location": {"lat": 30.0444, "lng": 31.2357},
        "eta_mins": 10,
    }


@router.get("/DRONE_SIMULATE")
def drone_simulate(route: str):
    """Simulates drone flight feasibility and ETA."""
    print(f"--- TOOL CALLED: DRONE_SIMULATE for route: '{route}' ---")
    return {
        "feasible": True,
        "eta_mins": random.randint(10, 15),
        "risk_score": round(random.uniform(0.05, 0.2), 2),
    }


@router.get("/USER_MEMORY_READ")
def user_memory_read(userId: str):
    """Simulates reading from the user's mid-term memory profile."""
    print(f"--- TOOL CALLED: USER_MEMORY_READ for user: '{userId}' ---")
    return FAKE_USER_MEMORY_DB.get(userId, {})


@router.post("/USER_MEMORY_WRITE")
def user_memory_write(userId: str, key: str, value: Any):
    """Simulates writing to the user's mid-term memory profile."""
    print(f"--- TOOL CALLED: USER_MEMORY_WRITE for user: '{userId}' ---")
    if userId not in FAKE_USER_MEMORY_DB:
        FAKE_USER_MEMORY_DB[userId] = {}
    FAKE_USER_MEMORY_DB[userId][key] = value
    return {"status": "success", "data": FAKE_USER_MEMORY_DB[userId]}


@router.get("/WEATHER_API")
def weather_api(location: str = "Cairo"):
    """Simulates getting weather data for a location."""
    print(f"--- TOOL CALLED: WEATHER_API for location: '{location}' ---")
    return {
        "conditions": "Clear",
        "wind_speed_kph": random.randint(5, 15),
        "rain_prob": round(random.uniform(0.0, 0.1), 2),
    }


@router.get("/TRAFFIC_API")
def traffic_api(route: str = "default_route"):
    """Simulates getting air traffic data for a drone route."""
    print(f"--- TOOL CALLED: TRAFFIC_API for route: '{route}' ---")
    return {"delay_mins": random.randint(0, 3)}

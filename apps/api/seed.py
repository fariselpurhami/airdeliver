# apps/api/seed.py

import asyncio
import json
import os
import sys
from typing import List
from sqlmodel import select, SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.core.config import settings
from app.models.product import Product
from app.models.user import User
from app.models.ai_cart import AIOrderingCartItem
from app.models.order import Order, OrderItem
from app.core.security import get_password_hash


if settings.APP_ENV != "development":
    print(f"ERROR: Seeding is disabled in '{settings.APP_ENV}' environment.")
    print("Set APP_ENV=development in your .env file to run the seeder.")
    sys.exit(1)

engine = create_async_engine(str(settings.DATABASE_URI), echo=False)
SEED_DATA_FILE = "seed_data.json"


async def clear_data(session: AsyncSession):
    print("Clearing old data...")

    all_cart_items_result = await session.execute(select(AIOrderingCartItem))
    all_cart_items = all_cart_items_result.scalars().all()
    for item in all_cart_items:
        await session.delete(item)
    print(f"Deleted {len(all_cart_items)} old AI cart items.")

    all_order_items_result = await session.execute(select(OrderItem))
    all_order_items = all_order_items_result.scalars().all()
    for item in all_order_items:
        await session.delete(item)
    print(f"Deleted {len(all_order_items)} old order items.")

    all_orders_result = await session.execute(select(Order))
    all_orders = all_orders_result.scalars().all()
    for item in all_orders:
        await session.delete(item)
    print(f"Deleted {len(all_orders)} old orders.")

    all_products_result = await session.execute(select(Product))
    all_products = all_products_result.scalars().all()
    for product in all_products:
        await session.delete(product)
    print(f"Deleted {len(all_products)} old products.")

    await session.commit()


async def create_superuser(session: AsyncSession):
    print("Checking for superuser...")
    user_in_db_result = await session.execute(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    )
    user_in_db = user_in_db_result.scalars().first()

    if not user_in_db:
        print("Creating default superuser...")
        user = User(
            email=settings.FIRST_SUPERUSER,
            full_name="Admin User",
            hashed_password=get_password_hash(settings.FIRST_SUPERUSER_PASSWORD),
            is_superuser=True, 
            role="admin",
            is_active=True,
        )
        session.add(user)
        await session.commit()
        print("Default superuser created.")
    else:
        print("Superuser already exists.")


async def seed_products(session: AsyncSession):
    print("Loading seed data from JSON...")
    try:
        with open(SEED_DATA_FILE, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: '{SEED_DATA_FILE}' not found.")
        print("Make sure it is in the same directory as seed.py.")
        return
    except json.JSONDecodeError:
        print(f"ERROR: Could not decode JSON from '{SEED_DATA_FILE}'.")
        return

    products_data = data.get("products", [])
    if not products_data:
        print("No products found in JSON file.")
        return

    print(f"Found {len(products_data)} products in JSON. Seeding...")

    products_to_create = []
    for p_data in products_data:
        if "id" not in p_data:
            print(f"Skipping product '{p_data.get('name')}' - Missing 'id'.")
            continue

        product = Product(**p_data)
        products_to_create.append(product)

    session.add_all(products_to_create)
    await session.commit()
    print(f"Successfully seeded {len(products_to_create)} products.")


async def seed_db():
    print("--- Starting Database Seed (Async) ---")

    async with AsyncSession(engine) as session:
        
        await clear_data(session)
        
        await create_superuser(session)
        
        await seed_products(session)

    print("--- Database Seeding Complete ---")


if __name__ == "__main__":
    asyncio.run(seed_db())

# apps/api/app/db/initial_data.py

import logging
import json
import os
from sqlmodel import Session, select, create_engine
from app import models
from app.core.config import get_core_settings
from app.core.security import get_password_hash

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_superuser(session: Session, settings):
    logger.info("🛡️  Security Protocol: Checking Superuser integrity...")
    
    admin_email = settings.FIRST_SUPERUSER
    admin_password = settings.FIRST_SUPERUSER_PASSWORD

    if not admin_email or not admin_password:
        logger.error("❌ FIRST_SUPERUSER credentials not set.")
        return

    # Check if admin exists
    user_in_db = session.exec(
        select(models.User).where(models.User.email == admin_email)
    ).first()

    if not user_in_db:
        logger.info(f"🆕 Creating System Administrator: {admin_email}")
        user = models.User(
            email=admin_email,
            full_name="System Admin",
            hashed_password=get_password_hash(admin_password),
            is_superuser=True, 
            role="admin",
            is_active=True,
        )
        session.add(user)
        session.commit()
        logger.info("✅ Superuser created successfully.")
    else:
        logger.info("✅ Superuser verification passed (Already exists).")

def seed_products_from_json(session: Session):
    logger.info("📦 Catalog Sync: Checking Base Inventory...")
    
    json_file_path = "seed_data.json" # Ensure this file exists in /app
    
    try:
        if not os.path.exists(json_file_path):
            # Fallback path if running from different context
            json_file_path = "/app/seed_data.json"
            
        with open(json_file_path, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.warning(f"⚠️  Seed file '{json_file_path}' not found. Skipping base products.")
        return
    except json.JSONDecodeError:
        logger.error(f"❌ FATAL: Could not decode JSON from '{json_file_path}'.")
        return

    products_data = data.get("products", [])
    if not products_data:
        logger.warning("⚠️  No products found in JSON file.")
        return

    # ARCHITECTURAL FIX: UPSERT LOGIC (Update or Insert)
    # Instead of skipping if DB is full, we check for specific SKUs.
    
    added_count = 0
    for p_data in products_data:
        # We use SKU as the unique identifier for base products
        sku = p_data.get("sku")
        if not sku:
            continue

        existing_product = session.exec(
            select(models.Product).where(models.Product.sku == sku)
        ).first()

        if not existing_product:
            # Create new base product
            p_data.pop("id", None) # Ensure ID is auto-generated
            product = models.Product(**p_data)
            session.add(product)
            added_count += 1
    
    if added_count > 0:
        session.commit()
        logger.info(f"✅ Injected {added_count} Missing Base Products into the Catalog.")
    else:
        logger.info("✅ Base Inventory is synchronized (All base products exist).")


def init_db():
    logger.info("--- 🚀 STARTING SYSTEM INITIALIZATION 🚀 ---")
    settings = get_core_settings()
    
    # Fix driver string for synchronous connection
    sync_uri = str(settings.DATABASE_URI).replace(
        "postgresql+asyncpg", "postgresql+psycopg2"
    )
    
    sync_engine = create_engine(sync_uri)

    with Session(sync_engine) as session:
        create_superuser(session, settings)
        seed_products_from_json(session)

    logger.info("--- ✅ SYSTEM INITIALIZATION COMPLETE ---")

if __name__ == "__main__":
    init_db()

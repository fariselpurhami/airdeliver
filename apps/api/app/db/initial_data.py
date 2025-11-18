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
    logger.info("Checking for superuser...")
    
    admin_email = settings.FIRST_SUPERUSER
    admin_password = settings.FIRST_SUPERUSER_PASSWORD

    if not admin_email or not admin_password:
        logger.error("FIRST_SUPERUSER or FIRST_SUPERUSER_PASSWORD not set. Skipping superuser creation.")
        return

    user_in_db = session.exec(
        select(models.User).where(models.User.email == admin_email)
    ).first()

    if not user_in_db:
        logger.info(f"Creating default superuser: {admin_email}")
        user = models.User(
            email=admin_email,
            full_name="Admin User",
            hashed_password=get_password_hash(admin_password),
            is_superuser=True, 
            role="admin",
            is_active=True,
        )
        session.add(user)
        session.commit()
        logger.info("Default superuser created.")
    else:
        logger.info("Superuser already exists.")

def seed_products_from_json(session: Session):
    logger.info("Checking for products...")
    products = session.exec(select(models.Product)).first()
    
    if products:
        logger.info("Database already seeded with products. Skipping.")
        return

    logger.info("No products found. Seeding from seed_data.json...")
    
    json_file_path = "seed_data.json"
    
    try:
        with open(json_file_path, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.error(f"FATAL: '{json_file_path}' not found. Make sure it is in /app directory.")
        return
    except json.JSONDecodeError:
        logger.error(f"FATAL: Could not decode JSON from '{json_file_path}'.")
        return

    products_data = data.get("products", [])
    if not products_data:
        logger.warning("No products found in JSON file.")
        return

    products_to_create = []
    for p_data in products_data:
        p_data.pop("id", None) 
        product = models.Product(**p_data)
        products_to_create.append(product)

    session.add_all(products_to_create)
    session.commit()
    logger.info(f"Successfully seeded {len(products_to_create)} products from JSON.")


def init_db():
    logger.info("--- Initializing Service Data (Synchronous) ---")
    settings = get_core_settings()
    
    # -----------------------------------------------------------------
    # 🚀 [الحل المعماري العالمي]
    # 1. اقرأ سلسلة الاتصال (التي تحتوي على 'asyncpg' الخاطئ).
    # 2. قم بـ "فرض" (Force) استبدال برنامج التشغيل غير المتزامن ('asyncpg')
    #    ببرنامج تشغيل متزامن ('psycopg2').
    # 3. هذا يجعل السكريبت مرنًا (Resilient) ضد أخطاء .env.
    # -----------------------------------------------------------------
    
    sync_uri = str(settings.DATABASE_URI).replace(
        "postgresql+asyncpg", "postgresql+psycopg2"
    )
    
    if "asyncpg" in sync_uri:
         logger.warning("Failed to replace asyncpg driver. Retrying with simple replacement.")
         sync_uri = str(settings.DATABASE_URI).replace(
             "asyncpg", "psycopg2"
         )

    sync_engine = create_engine(sync_uri)

    with Session(sync_engine) as session:
        create_superuser(session, settings)
        seed_products_from_json(session)

    logger.info("--- Data Initialization Complete ---")

if __name__ == "__main__":
    init_db()

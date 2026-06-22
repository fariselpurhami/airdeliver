# apps/api/app/db/initial_data.py

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Set

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from app import models
from app.core.config import get_core_settings
from app.core.security import get_password_hash
from app.db.session import sync_engine  # Assumes sync engine is properly exported here

# Configure logging locally to this module, avoiding global basicConfig side-effects
logger = logging.getLogger(__name__)

# Deterministic path resolution: Resolve relative to this file's location
# e.g., apps/api/app/db/initial_data.py -> apps/api/app/seed_data.json
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SEED_FILE_PATH = PROJECT_ROOT / "seed_data.json"


def create_superuser(session: Session, settings: Any) -> None:
    """Idempotent operation to ensure the system administrator exists."""
    logger.info("🛡️ Security Protocol: Verifying Superuser integrity...")

    admin_email = settings.FIRST_SUPERUSER
    admin_password = settings.FIRST_SUPERUSER_PASSWORD

    if not admin_email or not admin_password:
        logger.error("❌ FIRST_SUPERUSER or FIRST_SUPERUSER_PASSWORD credentials not configured.")
        raise ValueError("Missing critical superuser configuration.")
    raw_password = admin_password.get_secret_value() if hasattr(admin_password, "get_secret_value") else admin_password
    try:
        user_in_db = session.execute(
            select(models.User).where(models.User.email == admin_email)
        ).first()

        if user_in_db:
            logger.info("✅ Superuser verification passed (Already exists).")
            return

        logger.info(f"🆕 Provisioning System Administrator: {admin_email}")
        user = models.User(
            email=admin_email,
            full_name="Admin",
            hashed_password=get_password_hash(raw_password),
            is_superuser=True,
            role="admin",
            is_active=True,
        )

        session.add(user)
        session.commit()
        logger.info("✅ Superuser provisioned successfully.")

    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"❌ Database error during superuser creation: {str(e)}")
        raise


def load_seed_data(file_path: Path) -> List[Dict[str, Any]]:
    """Deterministically loads and parses seed data."""
    if not file_path.exists():
        logger.warning(f"⚠️ Seed file '{file_path}' not found. Skipping base inventory sync.")
        return []

    try:
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("products", [])
    except json.JSONDecodeError as e:
        logger.error(f"❌ FATAL: JSON decoding failed for '{file_path}': {str(e)}")
        raise


def seed_products(session: Session, products_data: List[Dict[str, Any]]) -> None:
    """
    Synchronizes catalog using bulk queries to avoid N+1 anti-patterns.
    Maintains strict transaction boundaries.
    """
    if not products_data:
        logger.info("ℹ️ No product data provided for seeding.")
        return

    logger.info("📦 Catalog Sync: Synchronizing Base Inventory...")

    try:
        # 1. Extract all target SKUs to query in bulk
        incoming_skus: Set[str] = {p.get("sku") for p in products_data if p.get("sku")}
        
        if not incoming_skus:
            logger.warning("⚠️ No valid SKUs found in seed data.")
            return

        # 2. Bulk fetch existing SKUs (Eliminates N+1 DB calls)
        existing_products = session.execute(
            select(models.Product.sku).where(models.Product.sku.in_(incoming_skus))
        ).all()
        existing_skus: Set[str] = set(existing_products)

        # 3. Filter for truly new products
        new_products = []
        for p_data in products_data:
            sku = p_data.get("sku")
            if sku and sku not in existing_skus:
                p_data.pop("id", None)  # Enforce DB-generated IDs
                new_products.append(models.Product(**p_data))

        # 4. Bulk insert if missing
        if new_products:
            session.add_all(new_products)
            session.commit()
            logger.info(f"✅ Injected {len(new_products)} missing base products into the catalog.")
        else:
            logger.info("✅ Base Inventory is synchronized (All base products exist).")

    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"❌ Database error during product synchronization: {str(e)}")
        raise


def init_db() -> None:
    """Orchestrates database initialization with strict boundary control."""
    logger.info("--- 🚀 INITIATING SYSTEM BOOTSTRAP 🚀 ---")
    settings = get_core_settings()

    # Use a centrally configured synchronous engine instead of hacky string replacement
    # Fallback only if architecture explicitly failed to provide the sync engine.
    try:
        with Session(sync_engine) as session:
            create_superuser(session, settings)
            
            products_data = load_seed_data(SEED_FILE_PATH)
            seed_products(session, products_data)
            
        logger.info("--- ✅ SYSTEM BOOTSTRAP COMPLETE ---")
        
    except Exception as e:
        logger.error(f"💥 FATAL: System bootstrap failed: {str(e)}")
        raise SystemExit(1)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    init_db()

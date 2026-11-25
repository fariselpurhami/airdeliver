# backend/api/init_data.py

import asyncio
import logging
import sys
import os
import time

# --- 🧱 Core Architectural Imports ---
from sqlmodel import select
from app.db.session import SessionLocal
from app.core.security import get_password_hash
from app.core.config import get_core_settings
from app.models.user import User
from app.models.enums import UserRole

# --- 🏭 Factory Imports (CORRECTED) ---
# 👇 نستورد الدوال الصحيحة الموجودة فعلياً في ملفك
from seed_ultra_scale import seed_sql, seed_search_engines

# --- 🎛️ Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("airdeliver.orchestrator")

# --- 🔐 PHASE 0: Identity Provisioning Protocol ---
async def ensure_super_admin():
    """
    Ensures the existence of the Root Super Admin.
    """
    logger.info("👤 [PHASE 0] INITIALIZING IDENTITY LAYER...")
    settings = get_core_settings()
    
    admin_email = settings.FIRST_SUPERUSER
    admin_password = settings.FIRST_SUPERUSER_PASSWORD
    
    if not admin_email or not admin_password:
        logger.warning("⚠️ [PHASE 0] SKIPPED: Missing FIRST_SUPERUSER credentials.")
        return

    async with SessionLocal() as session:
        statement = select(User).where(User.email == admin_email)
        result = await session.exec(statement)
        existing_user = result.first()
        
        if not existing_user:
            logger.info(f"🆕 Creating Global Super Admin: {admin_email}")
            new_admin = User(
                email=admin_email,
                full_name="Chief Architect",
                hashed_password=get_password_hash(admin_password),
                is_superuser=True,
                role=UserRole.SUPER_ADMIN,
                is_active=True
            )
            session.add(new_admin)
            await session.commit()
            logger.info("✅ [PHASE 0] SUPER ADMIN PROVISIONED SUCCESSFULLY.")
        else:
            logger.info("🛡️ [PHASE 0] Super Admin already active.")

# --- 🚀 Main Orchestrator ---
async def main():
    total_start = time.time()
    logger.info("🚦 SYSTEM INITIALIZATION PROTOCOL INITIATED")
    logger.info("==================================================")

    try:
        # 1️⃣ PHASE 0: USER IDENTITY
        p0_start = time.time()
        await ensure_super_admin()
        logger.info(f"✨ PHASE 0 COMPLETE IN {time.time() - p0_start:.2f}s")
        logger.info("--------------------------------------------------")

        # 2️⃣ PHASE 1: DATA MANUFACTURING (SQL)
        logger.info("🚀 EXECUTING PHASE 1: DATA MANUFACTURING (POSTGRESQL)")
        p1_start = time.time()
        # 👇 استدعاء الدالة الصحيحة من ملف seed_ultra_scale
        await seed_sql() 
        logger.info(f"✨ PHASE 1 COMPLETE IN {time.time() - p1_start:.2f}s")
        logger.info("--------------------------------------------------")

        # 3️⃣ PHASE 2: SEARCH SYNCHRONIZATION (Vector/Search)
        logger.info("💎 EXECUTING PHASE 2: SEARCH SYNCHRONIZATION (OPENSEARCH/MILVUS)")
        p2_start = time.time()
        # 👇 استدعاء الدالة الصحيحة من ملف seed_ultra_scale
        await seed_search_engines()
        logger.info(f"✨ PHASE 2 COMPLETE IN {time.time() - p2_start:.2f}s")
        logger.info("==================================================")

        total_duration = time.time() - total_start
        logger.info(f"🏁 AIRDELIVER INFRASTRUCTURE READY | TOTAL TIME: {total_duration:.2f}s")

    except Exception as e:
        logger.critical(f"🔥 FATAL INITIALIZATION ERROR: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    try:
        import uvloop
        uvloop.install()
        logger.info("🚀 uvloop activated for maximum throughput.")
    except ImportError:
        pass

    asyncio.run(main())

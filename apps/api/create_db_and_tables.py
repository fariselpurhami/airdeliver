# apps/api/create_db_and_tables.py

import os
import asyncio
import logging
import importlib.util
from pathlib import Path

from sqlmodel import SQLModel, create_engine
from app.core.config import get_core_settings

logger = logging.getLogger("db_init")
logger.setLevel(logging.INFO)

settings = get_core_settings()

# ⚠️ NOTE: Must use synchronous driver (psycopg2) for create_engine metadata access
DB_URI = str(settings.DATABASE_URI).replace("postgresql+asyncpg", "postgresql")

engine = create_engine(DB_URI, echo=False)

def _import_all_models():
    """ 
    🏆 ULTRA-SCALE REFINEMENT: Recursively imports all models in the 'app.models' 
    directory so SQLModel.metadata.create_all discovers them automatically.
    """
    models_dir = Path(__file__).parent.parent / "app" / "models"
    
    # Check if the models directory exists relative to the current script
    if not models_dir.is_dir():
        logger.warning(f"Models directory not found at: {models_dir}")
        return

    logger.info("🔍 Automatically discovering and importing models...")
    for file_path in models_dir.glob("*.py"):
        if file_path.name in ("__init__.py", "base.py"):
            continue
        
        module_name = f"app.models.{file_path.stem}"
        try:
            # Dynamically load the module to register SQLModel classes
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                logger.debug(f"   -> Imported: {module_name}")
        except Exception as e:
            logger.error(f"   -> Failed to import {module_name}: {e}")
            
    # CRITICAL: Import required modules explicitly if auto-discovery is risky
    # Ensures base models (like Product) are definitely loaded
    try:
        from app.models.product import Product
        # from app.models.user import User # Add other known models
    except ImportError:
        logger.warning("Core models not found in expected path.")


def create_db_and_tables():
    logger.info("��️ Attempting to create all database tables...")
    
    # 1. Discover all models dynamically
    _import_all_models() 
    
    # 2. Execute creation
    try:
        # This function relies on all SQLModel classes being imported into memory
        SQLModel.metadata.create_all(engine)
        logger.info("✅ Database tables created successfully (or already exist).")
    except Exception as e:
        logger.critical(f"❌ FATAL ERROR creating tables. Make sure the database is running and accessible. Error: {e}")

if __name__ == "__main__":
    create_db_and_tables()

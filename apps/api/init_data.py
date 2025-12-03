# apps/api/init_data.py       

import asyncio
import logging
import sys
import os
import time

from seed_ultra_scale import seed_ultra
from sync_search import DiamondSearchSynchronizer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("airdeliver.orchestrator")

async def main():
    total_start = time.time()
    logger.info("🚦 SYSTEM INITIALIZATION PROTOCOL INITIATED")

    try:
        logger.info("🚀 EXECUTING PHASE 1: DATA MANUFACTURING (POSTGRESQL)")
        p1_start = time.time()
        await seed_ultra()
        p1_duration = time.time() - p1_start
        logger.info(f"✅ PHASE 1 COMPLETE IN {p1_duration:.2f}s")

        logger.info("💎 EXECUTING PHASE 2: SEARCH SYNCHRONIZATION (OPENSEARCH/MILVUS)")
        p2_start = time.time()
        synchronizer = DiamondSearchSynchronizer()
        await synchronizer.sync()
        p2_duration = time.time() - p2_start
        logger.info(f"✅ PHASE 2 COMPLETE IN {p2_duration:.2f}s")

        total_duration = time.time() - total_start
        logger.info(f"🏁 SYSTEM READY FOR DEPLOYMENT | TOTAL TIME: {total_duration:.2f}s")

    except Exception as e:
        logger.critical(f"🔥 FATAL INITIALIZATION ERROR: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    try:
        import uvloop
        uvloop.install()
    except ImportError:
        pass

    asyncio.run(main())

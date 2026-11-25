# backend/api/fix_milvus.py

from pymilvus import MilvusClient
from app.core.config import settings

def nuke_zombies():
    print("☢️  INITIALIZING MILVUS CLEANUP PROTOCOL...")
    client = MilvusClient(uri=settings.MILVUS_URI)
    
    # القائمة السوداء للمجموعات التي قد تسبب تعارضاً
    targets = [
        "airdeliver_visual_large_v1",  # الهدف الرئيسي
        "airdeliver_products_sota_v2",
        "airdeliver_intents_sota_v2",
        "airdeliver_memory_sota_v2"
    ]
    
    for col in targets:
        if client.has_collection(col):
            print(f"🔥 Dropping Zombie Collection: {col}")
            client.drop_collection(col)
        else:
            print(f"✅ Clean: {col} does not exist.")
            
    print("✨ MILVUS IS CLEAN. RESTART WORKER TO REBUILD SCHEMAS.")

if __name__ == "__main__":
    nuke_zombies()

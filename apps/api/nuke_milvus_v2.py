# apps/api/nuke_milvus_v2.py
from pymilvus import MilvusClient
from app.core.config import settings

def nuke_it_all():
    print("☢️  STARTING DEEP CLEAN PROTOCOL...")
    client = MilvusClient(uri=settings.MILVUS_URI)
    
    # 1. List EVERYTHING currently in DB
    existing_collections = client.list_collections()
    print(f"🧐 Found Collections in DB: {existing_collections}")
    
    # 2. List of targets to destroy
    targets = [
        "airdeliver_visual_large_v1", 
        "airdeliver_products_sota_v2",
        "airdeliver_intents_sota_v2",
        "airdeliver_memory_sota_v2",
        # القديم أيضاً للاحتياط
        "airdeliver_visual_sota_v1",
        "airdeliver_visual_sota_v2" 
    ]
    
    for col in targets:
        if col in existing_collections:
            print(f"💣 DROPPING: {col}")
            client.drop_collection(col)
        else:
            print(f"⚪ Clean: {col} not found.")
            
    print("✅ MILVUS WIPED CLEAN.")

if __name__ == "__main__":
    nuke_it_all()

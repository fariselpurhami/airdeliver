# apps/api/seed_ultra_scale.py

import asyncio
import random
import logging
import time
import os
import json  # Import JSON library
from typing import List, Dict, Any
from sqlalchemy import insert
from app.db.session import SessionLocal
from app.models.product import Product

# --- Enterprise Configuration ---
TARGET_COUNT = int(os.getenv("SEED_TARGET_COUNT", 100000))
BATCH_SIZE = int(os.getenv("SEED_BATCH_SIZE", 5000))

# --- Structured Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("airdeliver.factory")

class UltraProductFactory:
    """
    Diamond Standard Factory.
    Optimized for 'Dictionary Generation' instead of Object Instantiation.
    """
    def __init__(self):
        self.data = {
            "Electronics": {
                "images": ["/images/iphone-17-pro-max.jpg", "/images/earbuds.jpg", "/images/smart_speaker.jpg", "/images/case.jpeg"],
                "nouns": ["Phone", "Drone", "Laptop", "Camera", "Headset", "Tablet", "Console", "Router", "Monitor", "Keyboard", "Mouse", "Charger", "Gimbal", "Powerbank", "Projector", "Microphone", "VR Headset"],
                "brands": ["Apple", "Samsung", "Sony", "Dell", "HP", "Asus", "Logitech", "Razer", "Corsair", "DJI", "Canon", "Nikon", "Bose", "JBL", "Anker", "Xiaomi", "Huawei"],
                "adjectives": ["Pro", "Ultra", "Max", "Elite", "Gaming", "Wireless", "Smart", "4K", "Compact", "High-Speed", "Silent", "Mechanical", "Foldable", "Waterproof"]
            },
            "Fashion": {
                "images": ["/images/red_dress.jpg", "/images/suit.jpg", "/images/running_shoes.jpg", "/images/wallet.jpg"],
                "nouns": ["Jacket", "Dress", "Jeans", "T-Shirt", "Sneakers", "Boots", "Hoodie", "Blazer", "Scarf", "Hat", "Gloves", "Belt", "Skirt", "Coat", "Swimwear", "Loafers"],
                "brands": ["Nike", "Adidas", "Zara", "H&M", "Gucci", "Prada", "Levi's", "Calvin Klein", "Tommy Hilfiger", "Ralph Lauren", "Versace", "Dior", "Puma", "New Balance"],
                "adjectives": ["Slim-Fit", "Vintage", "Cotton", "Leather", "Denim", "Silk", "Casual", "Formal", "Summer", "Winter", "Classic", "Trendy", "Luxury", "Urban"]
            },
            "Beauty": {
                "images": ["/images/perfume.jpg"],
                "nouns": ["Perfume", "Lipstick", "Cream", "Serum", "Palette", "Mascara", "Eyeliner", "Foundation", "Brush Set", "Cleanser", "Toner", "Mask", "Oil"],
                "brands": ["Chanel", "Dior", "L'Oreal", "MAC", "Sephora", "Fenty", "Estee Lauder", "Maybelline", "Nivea", "Dove", "Kylie", "Huda Beauty", "The Ordinary"],
                "adjectives": ["Matte", "Glossy", "Hydrating", "Organic", "Vegan", "Anti-Aging", "Brightening", "Natural", "Long-Lasting", "Scented"]
            },
            "Home": {
                "images": ["/images/espresso_machine.jpg", "/images/yoga_mat.jpg"],
                "nouns": ["Coffee Maker", "Blender", "Lamp", "Pillow", "Rug", "Towels", "Planter", "Clock", "Mirror", "Vase", "Candle", "Organizer", "Mug"],
                "brands": ["IKEA", "Philips", "Nespresso", "Dyson", "Shark", "Ninja", "Generic", "HomeGoods", "West Elm"],
                "adjectives": ["Modern", "Minimalist", "Smart", "Automatic", "Cozy", "Soft", "Ceramic", "Wooden", "LED", "Eco-friendly"]
            },
            "Accessories": {
                "images": ["/images/watch.jpg", "/images/gold_necklace.jpg", "/images/wallet.jpg", "/images/cable.jpg"],
                "nouns": ["Watch", "Necklace", "Ring", "Bracelet", "Sunglasses", "Wallet", "Backpack", "Keychain", "Cap", "Beanie"],
                "brands": ["Rolex", "Casio", "Ray-Ban", "Fossil", "Pandora", "Swarovski", "Oakley", "G-Shock", "Cartier"],
                "adjectives": ["Gold", "Silver", "Diamond", "Leather", "Sport", "Aviator", "Polarized", "Classic", "Digital", "Analog"]
            }
        }

    def generate_batch_dicts(self, size: int) -> List[Dict[str, Any]]:
        batch = []
        categories_keys = list(self.data.keys())
        
        for _ in range(size):
            cat_name = random.choice(categories_keys)
            cat_data = self.data[cat_name]

            brand = random.choice(cat_data["brands"])
            noun = random.choice(cat_data["nouns"])
            adj = random.choice(cat_data["adjectives"])
            suffix = f"{random.randint(100, 9999)}"
            
            product_name = f"{brand} {adj} {noun} {suffix}"
            price = round(random.uniform(15.0, 1500.0), 2)
            img = random.choice(cat_data["images"])
            
            desc = f"Original {brand} {noun}. Features {adj.lower()} design. Drone ready."
            
            # List of tags
            tags_list = [cat_name.lower(), noun.lower(), brand.lower(), adj.lower(), "drone-delivery"]

            # --- DIAMOND FIX: Convert List to JSON String ---
            # This prevents the 'InterfaceError' with Core Insertions
            # If your DB column is JSON/JSONB in Postgres, this string will be cast automatically.
            # If it's ARRAY, SQLAlchemy might struggle with Core Insert, but JSON is safer here.
            # However, the safest bet for compatibility with the previous 'rvf5' error 
            # is to send it as a Python list IF the driver handles it, OR use ORM objects.
            
            # Let's stick to the Raw Dict but ensure tags are compatible.
            # Since we had an error before, I will switch this method to return ORM Objects.
            # It is slightly slower but 100% safer and guaranteed to work.
            pass 

    # --- ARCHITECTURAL DECISION: SWITCH TO ORM BULK SAVE ---
    # Reason: Core Insert proved unstable with your specific driver/column configuration.
    # ORM Bulk Save is robust and handles type conversion (List -> JSON/Array) automatically.
    
    def generate_batch_objects(self, size: int) -> List[Product]:
        batch = []
        categories_keys = list(self.data.keys())
        
        for _ in range(size):
            cat_name = random.choice(categories_keys)
            cat_data = self.data[cat_name]
            brand = random.choice(cat_data["brands"])
            noun = random.choice(cat_data["nouns"])
            adj = random.choice(cat_data["adjectives"])
            suffix = f"{random.randint(100, 9999)}"
            
            product_name = f"{brand} {adj} {noun} {suffix}"
            price = round(random.uniform(15.0, 1500.0), 2)
            img = random.choice(cat_data["images"])
            
            desc = f"Original {brand} {noun}. Features {adj.lower()} design."
            
            tags = [cat_name.lower(), noun.lower(), brand.lower(), adj.lower()]

            # Return Product Object (Safe)
            p = Product(
                name=product_name,
                description=desc,
                price=price,
                inventory=random.randint(50, 1000),
                image_url=img,
                category=cat_name.lower(),
                tags=tags, # ORM handles this perfectly
                rating=round(random.uniform(3.5, 5.0), 1)
            )
            batch.append(p)
        return batch

async def seed_ultra():
    logger.info(f"🏭 Starting ULTRA-SCALE Manufacturing (Enterprise ORM Mode).")
    logger.info(f"🎯 Target: {TARGET_COUNT:,} items | Batch Size: {BATCH_SIZE:,}")
    
    start_time = time.time()
    factory = UltraProductFactory()
    total_created = 0
    
    async with SessionLocal() as db:
        while total_created < TARGET_COUNT:
            step_start = time.time()
            
            remaining = TARGET_COUNT - total_created
            current_batch_size = min(BATCH_SIZE, remaining)
            
            # Use Object Generation (Safe Mode)
            products = factory.generate_batch_objects(current_batch_size)
            
            try:
                # Bulk Save Objects
                db.add_all(products)
                await db.commit()
                
                total_created += len(products)
                
                duration = time.time() - step_start
                rate = len(products) / duration if duration > 0 else 0
                logger.info(f"🚀 Batch Saved: {len(products)} items | Total: {total_created:,} | Speed: {rate:.0f} items/sec")
                
            except Exception as e:
                logger.error(f"🔥 Batch Failed: {e}")
                await db.rollback()
                break

    total_time = time.time() - start_time
    logger.info(f"✅ MISSION COMPLETE.")
    logger.info(f"📊 Statistics: {total_created:,} products in {total_time:.2f} seconds.")

if __name__ == "__main__":
    asyncio.run(seed_ultra())

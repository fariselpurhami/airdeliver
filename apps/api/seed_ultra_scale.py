# apps/api/seed_ultra_scale.py

import asyncio
import random
import logging
import time
import os
import json 
from typing import List
from app.db.session import SessionLocal
from app.models.product import Product

TARGET_COUNT = int(os.getenv("SEED_TARGET_COUNT", 100000))
BATCH_SIZE = int(os.getenv("SEED_BATCH_SIZE", 5000))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("airdeliver.factory")

class RealismFactory:
    """
    💎 DIAMOND STANDARD GENERATOR (Hybrid Mode)
    1. Preserves your 'Golden 14' original products.
    2. Generates 'High-Fidelity Synthetic Data' for the rest.
    """
    def __init__(self):
        self.catalog_blueprints = {
            "electronics": {
                "brands": ["Apple", "Samsung", "Sony", "Dell", "ASUS", "LG", "Bose", "JBL", "Logitech", "Razer", "Canon", "Nikon", "DJI", "GoPro"],
                "models": ["iPhone 15", "Galaxy S24", "WH-1000XM5", "XPS 15", "ROG Strix", "OLED C3", "QuietComfort", "Flip 6", "MX Master 3", "BlackWidow", "EOS R5", "Z8", "Mavic 3", "Hero 12"],
                "variants": ["Pro", "Ultra", "Max", "Elite", "Plus", "Mini", "Air", "Classic"],
                "specs": ["512GB", "1TB", "Wireless", "Noise Cancelling", "4K", "HDR", "Mechanical", "Bluetooth 5.3"],
                "colors": ["Midnight Black", "Silver", "Space Grey", "Gold", "White"],
                "theme": "111111/00C6FF"
            },
            "fashion": {
                "brands": ["Nike", "Adidas", "Zara", "Gucci", "H&M", "Levi's", "Calvin Klein", "Tommy Hilfiger", "Ralph Lauren", "Under Armour", "Puma", "North Face"],
                "models": ["Air Max", "Ultraboost", "Slim Fit Jeans", "Cotton Hoodie", "Leather Jacket", "Summer Dress", "Polo Shirt", "Running Shorts", "Winter Coat", "Blazer"],
                "variants": ["Vintage", "Modern", "Sport", "Classic", "Urban", "Streetwear", "Formal"],
                "specs": ["100% Cotton", "Genuine Leather", "Breathable", "Waterproof", "Stretch", "Slim Fit"],
                "colors": ["Navy Blue", "Red", "Black", "White", "Beige", "Olive Green"],
                "theme": "F5F5F5/333333"
            },
            "home": {
                "brands": ["IKEA", "Dyson", "Philips", "Nespresso", "KitchenAid", "Shark", "Ninja", "Samsung", "LG", "Nest"],
                "models": ["V15 Detect", "Air Fryer", "Smart Bulb", "Coffee Maker", "Blender", "Robot Vacuum", "Air Purifier", "Standing Desk", "Ergo Chair", "Smart Thermostat"],
                "variants": ["Pro", "Series 5", "Smart", "Automatic", "Compact", "XL"],
                "specs": ["Energy Saving", "WiFi Connected", "HEPA Filter", "Stainless Steel", "Voice Control"],
                "colors": ["Metallic", "White", "Matte Black", "Wood"],
                "theme": "E0E0E0/2C3E50"
            },
            "beauty": {
                "brands": ["L'Oreal", "Maybelline", "Chanel", "Dior", "Fenty", "Sephora", "The Ordinary", "CeraVe", "La Roche-Posay", "Estee Lauder"],
                "models": ["Matte Lipstick", "Night Serum", "Daily Moisturizer", "Foundation", "Mascara", "Perfume", "Sunscreen", "Face Cleanser", "Eye Cream", "Toner"],
                "variants": ["Hydrating", "Anti-Aging", "Glow", "Repair", "Volumizing", "Long-Lasting"],
                "specs": ["Vegan", "Cruelty-Free", "Vitamin C", "Hyaluronic Acid", "SPF 50"],
                "colors": ["Red", "Nude", "Pink", "Clear"],
                "theme": "FFD1DC/555555"
            },
            "accessories": {
                "brands": ["Rolex", "Casio", "Ray-Ban", "Fossil", "Pandora", "Swarovski", "Oakley", "G-Shock", "Cartier"],
                "models": ["Watch", "Necklace", "Ring", "Bracelet", "Sunglasses", "Wallet", "Backpack", "Keychain", "Cap", "Beanie"],
                "variants": ["Gold", "Silver", "Diamond", "Leather", "Sport", "Aviator", "Polarized", "Classic", "Digital", "Analog"],
                "specs": ["Water Resistant", "Genuine Leather", "UV Protection", "Handmade", "Stainless Steel"],
                "colors": ["Gold", "Silver", "Black", "Brown"],
                "theme": "1A1A1A/FFD700"
            }
        }

    def _generate_dynamic_image(self, category: str, name: str) -> str:
        cat_key = category.lower() if category.lower() in self.catalog_blueprints else "electronics"
        theme = self.catalog_blueprints[cat_key]["theme"]
        bg, fg = theme.split("/")
        clean_name = "+".join(name.split()[:3])
        return f"https://placehold.co/600x600/{bg}/{fg}?text={clean_name}"

    def load_base_products(self) -> List[Product]:
        """Loads the original 14 products from seed_data.json"""
        json_path = "seed_data.json"
        if not os.path.exists(json_path):
            logger.warning("⚠️ seed_data.json not found. Skipping base products.")
            return []
        
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
                products_data = data.get("products", [])
                
            base_products = []
            for p_data in products_data:
            
                if "tags" not in p_data: p_data["tags"] = []
                
                product = Product(**p_data)
                base_products.append(product)
                
            logger.info(f"📦 Loaded {len(base_products)} Base Products from JSON.")
            return base_products
        except Exception as e:
            logger.error(f"❌ Failed to load base products: {e}")
            return []

    def generate_batch(self, size: int) -> List[Product]:
        batch = []
        categories = list(self.catalog_blueprints.keys())
        
        for _ in range(size):
            cat = random.choice(categories)
            blueprint = self.catalog_blueprints[cat]
            
            brand = random.choice(blueprint["brands"])
            model = random.choice(blueprint["models"])
            variant = random.choice(blueprint["variants"])
            spec = random.choice(blueprint["specs"])
            
            product_name = f"{brand} {model} {variant}"
            
            desc = (
                f"Experience the new {product_name}. Featuring advanced {spec} technology. "
                f"Designed by {brand} for the modern lifestyle. "
                f"Perfect for those who demand quality and performance in the {cat} category."
            )
            
            price = round(random.uniform(20.0, 2000.0), 2)
            if price > 1000: price = 999.99
            
            img_url = self._generate_dynamic_image(cat, product_name)
            
            tags = [
                cat, 
                brand.lower(), 
                model.lower().split()[0], 
                "drone-ready",
                "fast-delivery"
            ]
            if "Pro" in variant or price > 500: tags.append("premium")
            if price < 50: tags.append("budget")

            p = Product(
                name=product_name,
                description=desc,
                price=price,
                inventory=random.randint(10, 500),
                image_url=img_url,
                category=cat,
                tags=tags,
                rating=round(random.uniform(4.0, 5.0), 1)
            )
            batch.append(p)
            
        return batch

async def seed_ultra():
    logger.info(f"🏭 Starting ULTRA-REALISM Manufacturing Plant.")
    logger.info(f"�� Target: {TARGET_COUNT:,} items | Batch Size: {BATCH_SIZE:,}")
    
    start_time = time.time()
    factory = RealismFactory()
    total_created = 0
    
    async with SessionLocal() as db:
        
        base_products = factory.load_base_products()
        if base_products:
            
            try:
                db.add_all(base_products)
                await db.commit()
                total_created += len(base_products)
                logger.info(f"✅ Inserted {len(base_products)} Base Products successfully.")
            except Exception as e:
                logger.warning(f"⚠️ Could not insert base products (maybe duplicates?): {e}")
                await db.rollback()

        while total_created < TARGET_COUNT:
            step_start = time.time()
            
            remaining = TARGET_COUNT - total_created
            current_batch_size = min(BATCH_SIZE, remaining)
            
            products = factory.generate_batch(current_batch_size)
            
            try:
                db.add_all(products)
                await db.commit()
                
                total_created += len(products)
                
                duration = time.time() - step_start
                rate = len(products) / duration if duration > 0 else 0
                logger.info(f"🚀 Generated: {len(products)} units | Total: {total_created:,} | Speed: {rate:.0f} items/sec")
                
            except Exception as e:
                logger.error(f"🔥 Batch Failed: {e}")
                await db.rollback()
                break

    total_time = time.time() - start_time
    logger.info(f"✅ MISSION COMPLETE.")
    logger.info(f"📊 Statistics: {total_created:,} realistic products generated in {total_time:.2f} seconds.")

if __name__ == "__main__":
    asyncio.run(seed_ultra())

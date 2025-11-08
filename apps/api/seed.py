from sqlmodel import Session, SQLModel, create_engine, select
from app.core.config import settings
from app.models.product import Product
from app.models.user import User
from app.models.ai_cart import AIOrderingCartItem
from app.core.security import get_password_hash

engine = create_engine(str(settings.DATABASE_URI), echo=False)

def seed_db():
    print("Seeding database...")

    with Session(engine) as session:
    
        user_in_db = session.exec(select(User).where(User.email == settings.FIRST_SUPERUSER)).first()
        if not user_in_db:
            print("Creating default superuser...")
            user = User(
                email=settings.FIRST_SUPERUSER,
                hashed_password=get_password_hash(settings.FIRST_SUPERUSER_PASSWORD),
                is_superuser=True, 
                role="ADMIN" 
            )
            session.add(user)
            session.commit()
            print("Default superuser created.")
        else:
            print("Superuser already exists.")

        print("Deleting all existing products to ensure a fresh seed...")

        print("Deleting all existing AI cart items first...")
        all_cart_items = session.exec(select(AIOrderingCartItem)).all()
        for item in all_cart_items:
            session.delete(item)
        print(f"Deleted {len(all_cart_items)} old AI cart items.")

        all_products = session.exec(select(Product)).all()
        for product in all_products:
            session.delete(product)
        session.commit()
        print(f"Deleted {len(all_products)} old products.")

        session.commit()

        print("Seeding initial products with smart tags and categories...")
        initial_products = [
            Product(
                name="Iphone 17 Pro Max", 
                description="The latest iPhone model. Perfect gift and premium device.", 
                price=1299.99, 
                inventory=50, 
                image_url="/images/iphone-17-pro-max.jpg", 
                category="electronics", 
                tags=["phone", "smartphone", "premium", "gift", "expensive"]
            ),
            Product(
                name="Cable Type C", 
                description="A durable USB-C to USB-C cable. Essential accessory.", 
                price=29.99, 
                inventory=200, 
                image_url="/images/cable.jpg", 
                category="accessories", 
                tags=["cable", "usb", "charge", "cheap", "budget", "affordable"]
            ),
            Product(
                name="iPhone Case Leather", 
                description="A premium leather case for iPhone. Protect your investment.", 
                price=59.99, 
                inventory=100, 
                image_url="/images/case.jpeg", 
                category="accessories", 
                tags=["case", "leather", "protection", "gift", "premium"]
            ),
            Product(
                name="Apple Watch Ultra 3", 
                description="The latest Apple Watch series. Great for fitness and style.", 
                price=799.99, 
                inventory=75, 
                image_url="/images/watch.jpg", 
                category="electronics", 
                tags=["watch", "smartwatch", "fitness", "premium", "sport", "gift", "running"]
            ),
            Product(
                name="Business Suit Black", 
                description="A sharp black suit. Essential for interviews and formal events.", 
                price=399.99, 
                inventory=20, 
                image_url="/images/suit.jpg", 
                category="clothing", 
                tags=["suit", "formal", "business", "interview", "men", "job", "meeting"]
            ),
            Product(
                name="Luxury Perfume", 
                description="A beautiful, long-lasting perfume. The perfect gift for her.", 
                price=199.99, 
                inventory=30, 
                image_url="/images/perfume.jpg", 
                category="beauty", 
                tags=["perfume", "gift", "women", "luxury", "girlfriend", "wife", "present"]
            ),
            Product(
                name="Men's Running Shoes",
                description="High-performance running shoes for athletes. Perfect for workout and sport.",
                price=129.99,
                inventory=150,
                image_url="/images/running_shoes.jpg",
                category="shoes",
                tags=["shoes", "sport", "running", "fitness", "men", "workout"]
            ),
            Product(
                name="Pro Yoga Mat",
                description="Eco-friendly non-slip yoga mat. Ideal for home workouts.",
                price=45.50,
                inventory=300,
                image_url="/images/yoga_mat.jpg",
                category="sport",
                tags=["sport", "fitness", "yoga", "workout", "women", "gift", "budget"]
            ),
            Product(
                name="Red Evening Dress",
                description="Stunning formal evening dress for special occasions like parties.",
                price=249.99,
                inventory=30,
                image_url="/images/red_dress.jpg",
                category="clothing",
                tags=["dress", "clothing", "formal", "party", "women", "luxury"]
            ),
            Product(
                name="18k Gold Necklace",
                description="A timeless 18-karat gold necklace. The perfect luxury gift.",
                price=550.00,
                inventory=15,
                image_url="/images/gold_necklace.jpg",
                category="jewelry",
                tags=["jewelry", "gift", "women", "girlfriend", "wife", "premium", "luxury", "expensive"]
            ),
            Product(
                name="Wireless Earbuds Pro",
                description="Noise-cancelling wireless earbuds with charging case. Great budget gift.",
                price=79.99,
                inventory=250,
                image_url="/images/earbuds.jpg",
                category="electronics",
                tags=["electronics", "audio", "earbuds", "cheap", "budget", "gift", "affordable"]
            ),
            Product(
                name="Smart Speaker Mini",
                description="Voice-controlled smart speaker for your home. Plays music and answers questions.",
                price=149.00,
                inventory=80,
                image_url="/images/smart_speaker.jpg",
                category="electronics",
                tags=["electronics", "home", "smart", "audio", "gift"]
            ),
            Product(
                name="Espresso Machine",
                description="Automatic espresso machine for perfect coffee at home.",
                price=499.99,
                inventory=25,
                image_url="/images/espresso_machine.jpg",
                category="home",
                tags=["home", "kitchen", "coffee", "premium", "gift", "expensive"]
            ),
            Product(
                name="Men's Leather Wallet",
                description="A classic bifold leather wallet. A great gift for him.",
                price=89.99,
                inventory=120,
                image_url="/images/wallet.jpg",
                category="accessories",
                tags=["wallet", "leather", "men", "gift", "boyfriend", "husband"]
            )
        ]
        session.add_all(initial_products)
        session.commit()
        print(f"Successfully seeded {len(initial_products)} products.")

if __name__ == "__main__":
    seed_db()

# file: apps/api/seed.py 

from sqlmodel import Session, SQLModel, create_engine, select
from app.core.config import settings
from app.models.product import Product
from app.models.user import User
from app.core.security import get_password_hash

engine = create_engine(str(settings.DATABASE_URI), echo=True)

def seed_db():
    print("Ensuring tables are created...")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
    
        user_in_db = session.exec(select(User).where(User.email == settings.FIRST_SUPERUSER)).first()
        if not user_in_db:
            print("Creating default superuser...")
            user = User(
                email=settings.FIRST_SUPERUSER,
                hashed_password=get_password_hash(settings.FIRST_SUPERUSER_PASSWORD),
                is_superuser=True,
            )
            session.add(user)
            session.commit()
            print("Default superuser created.")
        else:
            print("Superuser already exists.")

        print("Deleting all existing products to ensure a fresh seed...")
        all_products = session.exec(select(Product)).all()
        for product in all_products:
            session.delete(product)
        session.commit()
        print(f"Deleted {len(all_products)} old products.")
        # --------------------------------------------------

        print("Seeding initial products with correct image_url paths...")
        initial_products = [
            Product(name="Iphone 17 Pro Max", description="The latest iPhone model.", price=1299.99, inventory=50, image_url="/images/iphone-17-pro-max.jpg", category="electronics"),
            Product(name="Cable Type C", description="A durable USB-C to USB-C cable.", price=29.99, inventory=200, image_url="/images/cable.jpg", category="accessories"),
            Product(name="iPhone Case Leather", description="A premium leather case.", price=59.99, inventory=100, image_url="/images/case.jpeg", category="accessories"),
            Product(name="Apple Watch", description="The latest Apple Watch series.", price=799.99, inventory=75, image_url="/images/watch.jpg", category="electronics"),
        ]
        session.add_all(initial_products)
        session.commit()
        print("Initial products seeded successfully.")

if __name__ == "__main__":
    seed_db()

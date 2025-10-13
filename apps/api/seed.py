# file: apps/api/seed.py

from sqlmodel import Session, SQLModel, create_engine, select
from app.core.config import settings
from app.models.product import Product
from app.models.user import User
from app.core.security import get_password_hash

# Use the same database engine as your main application
engine = create_engine(str(settings.DATABASE_URI), echo=True)

def seed_db():
    print("Ensuring tables are created...")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        # --- 1. Check for and create a default user ---
        user_in_db = session.exec(select(User).where(User.email == settings.FIRST_SUPERUSER)).first()
        if not user_in_db:
            print("No users found. Creating default superuser...")
            user = User(
                email="admin@example.com",
                hashed_password=get_password_hash("password"), # <-- We hardcoded the simple password here
                is_superuser=True,
            )

            session.add(user)
            session.commit()
            print("Default superuser created successfully.")
        else:
            print("Superuser already exists. Skipping user creation.")

        # --- 2. Check for and create initial products ---
        product_in_db = session.exec(select(Product)).first()
        if not product_in_db:
            print("No products found. Seeding initial products...")
            initial_products = [
                Product(name="Iphone 17 Pro Max", description="The latest iPhone model.", price=1299.99, inventory=50, image="iphone-17-pro-max.jpg", category="electronics"),
                Product(name="Cable Type C", description="A durable USB-C to USB-C cable.", price=29.99, inventory=200, image="cable.jpg", category="accessories"),
                Product(name="iPhone Case Leather", description="A premium leather case.", price=59.99, inventory=100, image="case.jpeg", category="accessories"),
                Product(name="Apple Watch", description="The latest Apple Watch series.", price=799.99, inventory=75, image="watch.jpg", category="electronics"),
            ]
            session.add_all(initial_products)
            session.commit()
            print("Initial products seeded successfully.")
        else:
            print("Products already exist. Skipping product seeding.")

if __name__ == "__main__":
    seed_db()

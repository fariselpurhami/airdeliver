# apps/api/app/db/initial_data.py

import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from sqlmodel import Session, select
from app.db.session import engine
from app import models

def seed_db():
    print("Checking if database needs to be seeded...")
    with Session(engine) as session:
        products = session.exec(select(models.Product)).first()
        if not products:
            print("No products found. Seeding initial data...")
            initial_products = [
                models.Product(name="Iphone 17 Pro Max", description="The latest iPhone model.", price=1299.99, inventory=50, image_url="/images/iphone-17-pro-max.jpg"),
                models.Product(name="Cable Type C", description="A durable USB-C to USB-C cable.", price=29.99, inventory=200, image_url="/images/cable.jpg"),
                models.Product(name="iPhone Case Leather", description="A premium leather case.", price=59.99, inventory=100, image_url="/images/case.jpeg"),
                models.Product(name="Apple Watch", description="The latest Apple Watch series.", price=799.99, inventory=75, image_url="/images/watch.jpg"),
            ]
            session.add_all(initial_products)
            session.commit()
            print("Initial products seeded successfully.")
        else:
            print("Database already seeded.")

if __name__ == "__main__":
    seed_db()

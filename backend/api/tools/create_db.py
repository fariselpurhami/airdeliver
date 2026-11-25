# backend/api/create_db.py

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import engine
from app.db.base_class import Base  
from app import models  

def create_database():
    print("Creating all database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")

if __name__ == "__main__":
    create_database()

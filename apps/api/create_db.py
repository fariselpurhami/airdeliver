# In airdeliver/apps/api/create_db.py

# This script's only job is to create the database tables.
# It ensures all models are loaded before creating the tables.

import os
import sys

# Add the current directory to the Python path to find the 'app' module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.session import engine
from app.db.base_class import Base  # This should be your SQLModel base
from app import models  # This triggers the models/__init__.py

def create_database():
    print("Creating all database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")

if __name__ == "__main__":
    create_database()

# backend/api/reset_db.py

from app.db.session import engine
from sqlmodel import SQLModel

print("Connecting to the database to reset it...")

SQLModel.metadata.drop_all(engine)
print("All tables dropped.")

SQLModel.metadata.create_all(engine)
print("All tables created.")

print("Database has been reset successfully.")

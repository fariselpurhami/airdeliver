# file: apps/api/reset_db.py
from app.db.session import engine
from sqlmodel import SQLModel

print("Connecting to the database to reset it...")

# This line will drop all tables from the database
SQLModel.metadata.drop_all(engine)
print("All tables dropped.")

# This line will create all the tables again, fresh and empty
SQLModel.metadata.create_all(engine)
print("All tables created.")

print("Database has been reset successfully.")

# apps/api/hash_password.py

import sys
from app.core.security import get_password_hash

def hash_my_password(password_to_hash):
    """
    Script to generate a secure password hash.
    """
    if not password_to_hash:
        print("Error: Please provide a password.")
        print("Usage: poetry run python hash_password.py 'your_new_password_here'")
        return

    hashed_password = get_password_hash(password_to_hash)
    print("--- Your Hashed Password ---")
    print(hashed_password)
    print("------------------------------")
    print("Copy the hash above (starting with $2b$...) and paste it in your database.")

if __name__ == "__main__":

    password = sys.argv[1] if len(sys.argv) > 1 else None
    hash_my_password(password)

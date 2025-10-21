# file: apps/api/app/core/limiter.py

from slowapi import Limiter
from slowapi.util import get_remote_address

# Define the limiter instance here
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

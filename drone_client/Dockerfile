# file: drone_client/Dockerfile
# Base image with Python and MAVSDK dependencies
FROM python:3.11-slim as builder

# Install MAVSDK dependencies and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install MAVSDK Python (adjust version if needed)
# Installing from source or wheels might be necessary depending on the system
# Using pip install for simplicity here, ensure it works for the target arch
RUN pip install --no-cache-dir mavsdk==1.4.1 # Example version, check latest stable

# --- Application Stage ---
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies (like websockets, dotenv, structlog)
COPY requirements.txt .
# Assuming you create a requirements.txt with:
# websockets
# python-dotenv
# structlog
RUN pip install --no-cache-dir -r requirements.txt

# Copy MAVSDK from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages/mavsdk /usr/local/lib/python3.11/site-packages/mavsdk
# Copy any other necessary MAVSDK shared libraries if installed differently

# Copy application code
COPY drone-control.py .

# Expose local admin API port (optional)
# EXPOSE 8080

# Command to run the companion
CMD ["python", "drone-control.py"]

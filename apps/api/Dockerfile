# --- Stage 1: Build Stage ---
FROM python:3.11-slim as builder

WORKDIR /app

# Install build tools and poetry
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential curl && \
    pip install poetry==1.8.3 && \
    rm -rf /var/lib/apt/lists/*

# Copy only necessary files for dependency installation
COPY poetry.lock pyproject.toml ./

# --- 💡 التغيير الرئيسي: استخدم poetry export ثم pip install ---
# 1. Export dependencies to requirements.txt
RUN poetry export --without dev --without-hashes -f requirements.txt -o requirements.txt

# 2. Install dependencies using pip into a target directory
#    Using --prefix=/install ensures packages go to /install/lib/pythonX.Y/site-packages
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# --- Optional Check (يمكن إزالته بعد التأكد من أنه يعمل) ---
RUN ls /install/lib/python3.11/site-packages/ | grep jose

# --- Stage 2: Production image ---
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app

RUN mkdir -p /usr/local/lib/python3.11/site-packages

# --- 💡 نسخ الحزم من المسار الجديد ---
# Copy installed packages from the specific prefix location in the builder stage
COPY --from=builder /install/lib/python3.11/site-packages/. /usr/local/lib/python3.11/site-packages/
# Copy potential executables installed by packages (e.g., uvicorn, alembic)
COPY --from=builder /install/bin /usr/local/bin

# Copy application code and necessary files AFTER installing dependencies
COPY ./app ./app
COPY ./alembic.ini ./
COPY ./alembic ./alembic
COPY ./seed.py ./

# Install curl for healthcheck in the final stage
RUN apt-get update && apt-get install -y curl --no-install-recommends && rm -rf /var/lib/apt/lists/*

HEALTHCHECK --interval=5s --timeout=3s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8000/ws/health || exit 1 # Added /health endpoint

EXPOSE 8000

# Run migrations then start the server
CMD ["bash", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]

# file: apps/api/Dockerfile
# version: 1.0.0
# date: 2025-09-23
# author: Gemini 2.5 Pro

# Stage 1: Build the application with Poetry
FROM python:3.11-slim as builder

WORKDIR /app

# Install poetry
RUN pip install poetry

# Copy only dependency files to leverage Docker layer caching
COPY poetry.lock pyproject.toml ./

# Install dependencies
RUN poetry config virtualenvs.create false && \
    poetry install --no-dev --no-interaction --no-ansi

# Stage 2: Create the final production image
FROM python:3.11-slim

WORKDIR /app

# Copy the installed dependencies from the builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /app ./

# Copy the application code
COPY ./app ./app

EXPOSE 8000

# Run alembic migrations and then start the server
CMD ["bash", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]

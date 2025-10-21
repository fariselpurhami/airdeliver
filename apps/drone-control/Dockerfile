# Stage 1: Build dependencies
FROM python:3.11 as builder

RUN pip install poetry==1.8.2

WORKDIR /app

COPY poetry.lock pyproject.toml ./

RUN poetry export -f requirements.txt --output requirements.txt --without-hashes


# Stage 2: Final production image
FROM python:3.11-slim

WORKDIR /app

COPY --from=builder /app/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Correctly copy all project files from the current directory
COPY . .

# Correctly run the app from main.py
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

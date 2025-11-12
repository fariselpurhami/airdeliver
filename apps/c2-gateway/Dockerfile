# apps/c2-gateway/Dockerfile

FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir "fastapi[all]" uvicorn aio_pika httpx structlog "python-jose[cryptography]" pydantic-settings

COPY ./app /app/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]

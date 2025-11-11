# file: drone_client/Dockerfile

FROM python:3.11-slim as builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir mavsdk==1.4.1 

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY --from=builder /usr/local/lib/python3.11/site-packages/mavsdk /usr/local/lib/python3.11/site-packages/mavsdk

COPY drone-control.py .

CMD ["python", "drone-control.py"]

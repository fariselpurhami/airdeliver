# 🚀 airdeliver Developer Runbook

Welcome to the airdeliver monorepo. This document is the primary technical guide for developers and operators.

---
## 1. Project Architecture

The platform is a microservices-oriented monorepo containing the following key services:

-   **`apps/web`**: The Next.js frontend application.
-   **`apps/api`**: The main FastAPI backend (handles users, products, orders, payments).
-   **`apps/drone-control`**: A separate FastAPI service for real-time drone communication.
-   **`infra/`**: Contains infrastructure-as-code (Kubernetes manifests, Grafana dashboards).
-   **`docs/`**: Contains high-level documentation (Disaster Recovery, etc.).

---
## 2. Local Development Setup

### Prerequisites
-   Docker & Docker Compose
-   Node.js v20+ & `pnpm`
-   Python v3.11+ & `poetry`

### Step-by-Step Guide

1.  **Clone the Repository:**
    ```bash
    git clone <repository-url>
    cd airdeliver
    ```

2.  **Install Frontend Dependencies:**
    ```bash
    cd apps/web && pnpm install && cd ../..
    ```

3.  **Install Backend Dependencies:**
    ```bash
    cd apps/api && poetry install && cd ../..
    cd apps/drone-control && poetry install && cd ../..
    ```

4.  **Configure Environment Variables:**
    -   Create a `.env.local` file in `apps/web`. A minimal setup requires `NEXTAUTH_SECRET` and `NEXTAUTH_URL=http://localhost:3000`.
    -   Create `.env` files in `apps/api` and `apps/drone-control`. They will work out-of-the-box with the Docker Compose setup.

5.  **Run the Entire Stack:**
    The `docker-compose.yml` file in the root is the simplest way to run all services, including the PostgreSQL database.
    ```bash
    docker-compose up --build
    ```
    -   Frontend will be available at `http://localhost:3000`.
    -   Main API will be at `http://localhost:8000`.
    -   Drone Control API will be at `http://localhost:8001`.

---
## 3. Testing & Simulation

### Running Tests

-   **Backend (`api`, `drone-control`):**
    ```bash
    cd apps/api
    poetry run pytest
    ```
-   **Frontend (`web`):**
    ```bash
    cd apps/web
    pnpm test
    ```

### Virtual Drone Simulation
To test the drone control system without hardware, run the virtual drone simulator.
```bash
# First, ensure the Drone Control service is running (via Docker Compose)
# Then, in a new terminal:
python3 drone-simulator/virtual_drone.py

# 🚀 airdeliver Developer Runbook

Welcome to the **airdeliver** monorepo — the unified codebase powering an intelligent, drone-enabled eCommerce ecosystem.
This guide is intended for developers, DevOps engineers, and operators managing, extending, or deploying the platform.

---

## 🧭 1. Project Architecture

**airdeliver** follows a **microservices-oriented monorepo architecture**, combining modular applications under a single, cohesive workspace.

### Core Components

* **`apps/web`** – Next.js frontend for the user-facing eCommerce experience.
* **`apps/api`** – Primary FastAPI backend managing users, orders, products, payments, and AI order flow.
* **`apps/drone-control`** – Dedicated FastAPI microservice for real-time drone communication and task orchestration.
* **`infra/`** – Infrastructure-as-code assets, including Kubernetes manifests, monitoring, and Grafana dashboards.
* **`docs/`** – High-level operational and recovery documentation.
* **`drone-simulator/`** – Virtual environment for testing drone logic without hardware dependencies.

---

## 🧩 2. Local Development Setup

### Prerequisites

Ensure the following tools are installed before starting development:

* **Docker & Docker Compose** (latest version)
* **Node.js v20+** and **pnpm v9+**
* **Python v3.11+** and **Poetry**

---

### Step-by-Step Setup

#### 1. Clone the Repository

```bash
git clone <repository-url>
cd airdeliver
```

#### 2. Install Frontend Dependencies

```bash
cd apps/web
pnpm install
cd ../..
```

#### 3. Install Backend Dependencies

```bash
cd apps/api && poetry install && cd ../..
cd apps/drone-control && poetry install && cd ../..
```

#### 4. Configure Environment Variables

Create the necessary environment files for local development:

* **Frontend (`apps/web/.env.local`)**

  ```
  NEXTAUTH_SECRET=your-secret
  NEXTAUTH_URL=http://localhost:3000
  ```
* **Backend (`apps/api/.env`, `apps/drone-control/.env`)**
  Preconfigured to work seamlessly with Docker Compose defaults.

#### 5. Run the Full Stack

The root-level `docker-compose.yml` launches the complete environment — APIs, database, and frontend.

```bash
docker-compose up --build
```

**Services will be available at:**

* 🌐 Frontend → [http://localhost:3000](http://localhost:3000)
* 📦 Main API → [http://localhost:8000](http://localhost:8000)
* 🚁 Drone Control API → [http://localhost:8001](http://localhost:8001)

---

## 🧪 3. Testing & Simulation

### Backend Testing

Run tests for both the eCommerce API and drone-control services:

```bash
cd apps/api
poetry run pytest
```

```bash
cd apps/drone-control
poetry run pytest
```

### Frontend Testing

Execute unit and integration tests using Jest and React Testing Library:

```bash
cd apps/web
pnpm test
```

---

### Virtual Drone Simulation

To simulate drone operations locally without real hardware:

1. Ensure the `drone-control` service is running.
2. Launch the simulator:

   ```bash
   python3 drone-simulator/virtual_drone.py
   ```

The simulator communicates with the Drone Control API, validating delivery routes, flight logic, and order handling.

---

## 🧱 4. Deployment Overview

### Local (Development)

Use **Docker Compose** for isolated, full-stack testing.

### Production (Cloud)

Deployed through **Kubernetes manifests** located in `/infra/`, featuring:

* Autoscaling deployments
* Load-balanced APIs
* Centralized logging (Prometheus + Grafana)
* Encrypted secret management

CI/CD is handled via **GitHub Actions**, including linting, security scans, and automated build pipelines.

---

## 📟 5. Monitoring & Observability

* **Prometheus** collects metrics from all active services.
* **Grafana** visualizes performance, uptime, and system health dashboards.
* Alerts are configured for:

  * API downtime
  * Drone mission errors
  * Payment service degradation

---

## 🧰 6. Developer Tips

* Use feature branches named `feature/<your-feature>` for all contributions.
* Run local tests before merging to maintain CI integrity.
* Keep dependencies updated through automated PRs (Dependabot).
* Follow type safety and linting rules enforced by ESLint and MyPy.

---

## 🛡️ 7. Security & Compliance

* All internal and external traffic uses **TLS 1.2+** encryption.
* API access is protected by **JWT-based authentication**.
* Sensitive credentials are stored in **Kubernetes Secrets**, never in source code.
* Refer to `SECURITY.md` for the full security policy.

---

## 📚 8. Reference Documents

| Document        | Purpose                                                         |
| --------------- | --------------------------------------------------------------- |
| **README.md**   | High-level project overview, stack, and setup.                  |
| **SECURITY.md** | Security guidelines, reporting policies, and response timeline. |
| **docs/**       | Disaster Recovery, Incident Response, and architecture notes.   |

---

**airdeliver — building the future of intelligent commerce and autonomous logistics.**

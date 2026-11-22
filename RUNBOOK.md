# 🚀 airdeliver Developer Runbook

Welcome to the **airdeliver** monorepo — the unified codebase powering an intelligent eCommerce ecosystem.
This guide is intended for developers, DevOps engineers, and operators managing, extending, or deploying the platform.

---

## 🧭 1. Project Architecture

**airdeliver** follows a **microservices-oriented monorepo architecture**, combining modular applications under a single, cohesive workspace.

### Core Components

* **`apps/web`** – Next.js frontend for the user-facing eCommerce experience.
* **`apps/api`** – Primary FastAPI backend managing users, orders, products, payments, and AI order flow.
* **`infra/`** – Infrastructure-as-code assets, including Kubernetes manifests, monitoring, and Grafana dashboards.
* **`docs/`** – High-level operational and recovery documentation.

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
```

#### 4. Configure Environment Variables

Create the necessary environment files for local development:

* **Frontend (`apps/web/.env.local`)**

  ```
  NEXTAUTH_SECRET=your-secret
  NEXTAUTH_URL=http://localhost:3000
  ```
* **Backend (`apps/api/.env`)**
  Preconfigured to work seamlessly with Docker Compose defaults.

#### 5. Run the Full Stack

The root-level `docker-compose.yml` launches the complete environment — APIs, database, and frontend.

```bash
docker-compose up --build
```

**Services will be available at:**

* 🌐 Frontend → [http://localhost:3000](http://localhost:3000)
* 📦 Main API → [http://localhost:8000](http://localhost:8000)

---

## 🧪 3. Testing & Simulation

### Backend Testing

Run the eCommerce API test suite:

```bash
cd apps/api
poetry run pytest
```

### Frontend Testing

Execute unit and integration tests using Jest and React Testing Library:

```bash
cd apps/web
pnpm test
```

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

## Manual root shortcuts

`make help` lists local developer shortcuts. `make up`, `make down`, `make restart`
and `make logs` consistently use docker-compose.yml plus docker-compose.dev.yml
and project airdeliver_dev. `down` retains data volumes. These commands are manual,
not invoked by CI or Compose. They do not install dependencies or migrate data.
`dev-auto-watch.sh` is optional, needs nodemon, and rebuilds that same combined
stack when architectural inputs change. It is not needed to run the app normally.

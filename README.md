# airdeliver

*we soar in the sky by delivering your orders.*

**Author:** Faris Elpurhami

---

## 🚀 Overview

**airdeliver** is a fully automated, intelligent eCommerce and drone delivery platform — designed for next-generation commerce.
It unifies online shopping, AI-powered order handling, and autonomous drone delivery in one production-grade system built for global scale and operational excellence.

---

## 🌍 Core Features

### 🛒 End-to-End eCommerce Platform

A modern, high-performance **Next.js** frontend and **FastAPI** backend delivering a seamless shopping experience from browsing to checkout.

### 🚁 Intelligent Drone Control System

A dedicated microservice manages the drone fleet in real time using **REST** and **WebSocket APIs**, supported by:

* Automated task queueing and mission scheduling.
* Dynamic no-fly zone compliance.
* Virtual simulation for development and testing.

### 💳 Global Payment Orchestration

A modular backend service routes payments intelligently across gateways (**Stripe**, **PayPal**, etc.) depending on region, with built-in failover and easy scalability.

### 📊 Advanced Observability

Integrated **Prometheus** and **Grafana** dashboards for complete visibility.
Centralized structured logging and defined **SLOs** ensure reliability in production environments.

### 🧱 Production-Ready Infrastructure

* **Docker Compose** for local development.
* **Kubernetes manifests** for autoscaling, CI/CD, and resilient deployments.

### 🧪 Comprehensive Testing

Automated **unit**, **integration**, and **load testing** for both frontend and backend.
Includes a **virtual drone simulator** for end-to-end validation without hardware.

---

## 🧠 Tech Stack

| Layer              | Technologies                                                                     |
| ------------------ | -------------------------------------------------------------------------------- |
| **Frontend**       | Next.js, React, TypeScript, Tailwind CSS, Framer Motion, Zustand                 |
| **Backend**        | FastAPI (Python), SQLModel, PostgreSQL, Alembic                                  |
| **Real-time**      | WebSockets                                                                       |
| **Infrastructure** | Docker, Kubernetes, Prometheus, Grafana, GitHub Actions                          |
| **Testing**        | Pytest (Backend), Jest & React Testing Library (Frontend), Locust (Load Testing) |
| **Monorepo**       | pnpm Workspaces                                                                  |

---

## 🏗️ Monorepo Structure

```
/airdeliver
├── apps/
│   ├── api/            # Main eCommerce Backend (FastAPI)
│   ├── drone-control/  # Drone Fleet Management Service (FastAPI)
│   └── web/            # Customer-Facing Frontend (Next.js)
├── docs/               # High-Level Documentation (DR, Incident Response)
├── drone-client/       # Python Client for Drone Hardware
├── drone-simulator/    # Virtual Drone Fleet for Testing
├── infra/              # Infrastructure-as-Code (Kubernetes, Grafana)
├── packages/           # Shared Libraries (UI Components, Configs)
├── README.md           # This File
├── RUNBOOK.md          # Developer & Operations Manual
└── SECURITY.md         # Security Policy
```

---

## ⚙️ Getting Started

### Prerequisites

* Docker & Docker Compose
* Node.js **v20+** and **pnpm v9+**
* Python **v3.11+** and **Poetry**

### Installation

```bash
# Clone the repository
git clone https://github.com/your-repo/airdeliver.git
cd airdeliver

# Install all dependencies
pnpm install
poetry install --all-extras
```

---

## 🧭 Running the Stack

### 1. Configure Environment Variables

Create `.env.local` inside `apps/web` with:

```
NEXTAUTH_SECRET=your-secret
NEXTAUTH_URL=http://localhost:3000
```

Backend `.env` files are preconfigured for Docker-based local development.

### 2. Launch with Docker Compose

```bash
docker-compose up --build
```

Once started:

* 🌐 **Frontend:** [http://localhost:3000](http://localhost:3000)
* 📦 **Main API:** [http://localhost:8000](http://localhost:8000)
* 🚁 **Drone Control API:** [http://localhost:8001](http://localhost:8001)

---

## 📚 Documentation

| Document        | Description                                                         |
| --------------- | ------------------------------------------------------------------- |
| **RUNBOOK.md**  | Complete guide for setup, deployment, migrations, and service SLOs. |
| **SECURITY.md** | Security measures and vulnerability reporting.                      |
| **docs/**       | Disaster Recovery, Incident Response, and architectural overviews.  |

---

## 🪪 License

This project is licensed under the **MIT License**.
See the `LICENSE` file for details.

---

**airdeliver — redefining how commerce takes flight.**


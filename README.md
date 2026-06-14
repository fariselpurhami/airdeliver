

```markdown
# 🛸 airdeliverOS
**The AI-Native Commerce Operating System for Autonomous eVTOL Delivery**

[![Monorepo](https://img.shields.io/badge/Architecture-Monorepo-black?style=flat-square&logo=pnpm)](https://pnpm.io/)
[![Next.js](https://img.shields.io/badge/Frontend-Next.js_14-black?style=flat-square&logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![AI Core](https://img.shields.io/badge/Neural_Engine-Qwen2_1.5B-blue?style=flat-square)](#)
[![Infrastructure](https://img.shields.io/badge/Deploy-Kubernetes_|_Docker-326ce5?style=flat-square&logo=kubernetes)](#)

> *Bridging the gap between digital intent and physical reality. We don't just process orders; we fly them to you.*

**Author:** Faris Elpurhami

---

## 🌌 Vision & Architecture

**airdeliver** is not just an application; it is a full-scale **Commerce Operating System (OS)**. It is built from the ground up to orchestrate the entire lifecycle of an autonomous transaction—from cognitive AI-driven user interactions to the physical routing of eVTOL (Electric Vertical Takeoff and Landing) fleets.

The system is decoupled into three primary pillars within a high-performance **pnpm Monorepo**:
1. **The Neural Commerce Engine (`apps/api`):** A sophisticated AI brain featuring embedded Meta-Cognition, NLU (Natural Language Understanding), and Vector Search (Milvus/PgVector) to process hybrid multimodal inputs (Voice, Vision, Text).
2. **The Command & Control Gateway (`apps/c2-gateway`):** An ultra-low latency, RabbitMQ/WebSocket-driven gateway that handles live fleet telemetry, no-fly zone compliance, and real-time eVTOL routing.
3. **The Immersive Client (`apps/web`):** A Next.js 14 App Router frontend delivering a 60FPS fluid UI, physics-based animations (Framer Motion), holographic flight tracking, and cinematic checkout experiences.

---

## 🧠 Core Subsystems

### 🤖 AI Behavior & Meta-Cognition Engine
* **Local SLM Integration:** Embedded `Alibaba-NLP/gte-Qwen2-1.5B-instruct` models for hyper-fast, privacy-preserving semantic routing and embedding generation.
* **Proactive State Management:** The AI doesn't just answer questions; it actively manages user carts, predicts intent, and triggers autonomous checkout recovery via the `ai_behavior_engine`.

### 🚁 eVTOL Fleet Command (C2)
* **Real-time Telemetry:** Live WebSocket pipelines streaming Drone GPS, Altitude, Speed, and Gyroscopic Stability directly to the user's browser.
* **Distributed Task Queueing:** Highly resilient message brokering via RabbitMQ to orchestrate fleet dispatches and mission state updates.

### 💳 Cryptographic Commerce & UI
* **Floating Mobile-Optimized Overlays:** Context-aware, AI-driven UI modules that act as desktop applets (`max-w-[460px]`) to maintain laser-focused conversion funnels.
* **Payment Orchestration:** Adaptive, multi-gateway secure tunneling (Stripe) with graceful failover mechanics.

---

## 🏗️ Monorepo Topography

Our workspace is structured for enterprise scalability and strict separation of concerns:

```text
/airdeliver
├── apps/
│   ├── api/                 # The Neural Engine (FastAPI, SQLModel, Vector DB)
│   │   ├── app/services/    # AI Cores (NLU, Meta-Cognition, Behavior Engine)
│   │   └── app/websockets/  # Live Tracking & Telemetry Pipelines
│   ├── c2-gateway/          # eVTOL Command & Control Router (RabbitMQ / WebSockets)
│   └── web/                 # Customer-Facing Frontend (Next.js 14, Zustand, Tailwind)
│       └── app/components/  # Cinematic UI, AI Voice Overlays, Holographic Dashboards
├── infra/                   # Infrastructure-as-Code
│   ├── k8s/                 # Kubernetes Manifests (Deployments, Ingress, Services)
│   └── grafana/             # Observability Dashboards
├── monitoring/              # Prometheus Configurations & Promtail Logs
├── data/                    # HuggingFace Model Caches & Persistent Volumes
├── tests/                   # End-to-End, Integration, and Global Architecture Tests
└── docs/                    # Architectural Decision Records (ADRs) & Runbooks

```

---

## 🛠️ Technology Stack

| Domain | Core Technologies |
| --- | --- |
| **Cognitive AI** | HuggingFace (Qwen2 1.5B), Vector DBs (Milvus/pgvector), Web Speech API |
| **Frontend Ecosystem** | Next.js 14, React, TypeScript, Tailwind CSS, Framer Motion, Zustand |
| **Backend Engines** | FastAPI (Python 3.11), SQLModel, Alembic, PostgreSQL |
| **Real-Time & Broker** | WebSockets, RabbitMQ, Redis |
| **Infrastructure** | Docker Compose, Kubernetes, NGINX |
| **Observability** | Prometheus, Grafana, Structured Logging |
| **Package Management** | `pnpm` Workspaces, `poetry` |

---

## ⚙️ Getting Started

### Prerequisites

* **Node.js** `v20+` and **pnpm** `v9+`
* **Python** `v3.11+` and **Poetry**
* **Docker** & Docker Compose
* *(Optional but recommended)* NVIDIA GPU with CUDA for local AI model acceleration.

### 1. Bootstrap the Ecosystem

```bash
git clone [https://github.com/fariselpurhami/airdeliver.git](https://github.com/fariselpurhami/airdeliver.git)
cd airdeliver

# Install frontend workspace dependencies
pnpm install

# Install backend dependencies
cd apps/api && poetry install

```

### 2. Configure Environment Secrets

Create local environment files. See `docs/` for necessary keys (Stripe, NextAuth, DB URLs).

* Frontend: `apps/web/.env.local`
* Backend/AI: `apps/api/.env`

### 3. Ignite the Cluster

Launch the entire localized microservices infrastructure (DBs, Message Brokers, APIs, C2 Gateway):

```bash
docker-compose up --build

```

> **Services Online:**
> * 🌐 **Web UI:** `http://localhost:3000`
> * 🧠 **API / Neural Core:** `http://localhost:8000`
> * 🚁 **C2 Gateway:** `http://localhost:8001`
> * 📊 **Grafana:** `http://localhost:3001`
> 
> 

---

## 🛡️ Operations & Reliability

For production deployments, disaster recovery, and architecture testing, please refer to our internal documentation:

* 📖 **[RUNBOOK.md](https://www.google.com/search?q=./RUNBOOK.md)** - System operations, scaling metrics, and SLOs.
* 🚨 **[INCIDENT_RESPONSE.md](https://www.google.com/search?q=./docs/INCIDENT_RESPONSE.md)** - Outage mitigation and failover strategies.
* 🧠 **[AI_ORDERING_AGENT.md](https://www.google.com/search?q=./docs/AI_ORDERING_AGENT.md)** - Behavior trees and prompt engineering architecture.
* 🔒 **[SECURITY.md](https://www.google.com/search?q=./SECURITY.md)** - Payload encryption and vulnerability protocols.

---

## 🪪 License

This project is proprietary and licensed under the conditions outlined in [LICENSE.txt](https://www.google.com/search?q=./LICENSE.txt).

---

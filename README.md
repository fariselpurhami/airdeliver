

```markdown
# airdeliverOS
**The AI-Native Commerce Platform**

[![Monorepo](https://img.shields.io/badge/Architecture-Monorepo-black?style=flat-square&logo=pnpm)](https://pnpm.io/)
[![Next.js](https://img.shields.io/badge/Frontend-Next.js_14-black?style=flat-square&logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![AI Core](https://img.shields.io/badge/Neural_Engine-Qwen2_1.5B-blue?style=flat-square)](#)
[![Infrastructure](https://img.shields.io/badge/Deploy-Kubernetes_|_Docker-326ce5?style=flat-square&logo=kubernetes)](#)

> *Bridging the gap between digital intent and physical reality. From question to order, handled by AI.*

**Author:** Faris Elpurhami

---

## 🌌 Vision & Architecture

**airdeliver** is built to orchestrate the entire lifecycle of an order—from cognitive AI-driven user interactions to payment and fulfillment with local partner stores.

The system is decoupled into two primary pillars within a **pnpm Monorepo**:
1. **The Neural Commerce Engine (`backend/api`):** The AI brain featuring NLU (Natural Language Understanding) and Vector Search (Milvus/PgVector) to process multimodal inputs (Voice, Vision, Text).
2. **The Immersive Client (`frontend/web`):** A Next.js 14 App Router frontend with physics-based animations (Framer Motion) and a cinematic checkout experience.

---

## 🧠 Core Subsystems

### 🤖 AI Behavior & Meta-Cognition Engine
* **Local SLM Integration:** Embedded `Alibaba-NLP/gte-Qwen2-1.5B-instruct` models for hyper-fast, privacy-preserving semantic routing and embedding generation.
* **Proactive State Management:** The AI doesn't just answer questions; it actively manages user carts, predicts intent, and triggers autonomous checkout recovery via the `ai_behavior_engine`.

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
│   │   ├── app/services/    # AI Cores (NLU, Behavior Engine, Cart/Checkout)
│   │   └── app/websockets/  # Live AI Chat Channel
│   └── web/                 # Customer-Facing Frontend (Next.js, Zustand, Tailwind)
│       └── app/components/  # Cinematic UI, AI Voice Overlays
├── infra/                   # Infrastructure-as-Code
│   ├── k8s/                 # Kubernetes Manifests (Deployments, Ingress, Services)
│   └── grafana/             # Observability Dashboards
├── infra/observability/     # Prometheus, Promtail and Grafana config
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
cd backend/api && poetry install

```

### 2. Configure Environment Secrets

Create local environment files. See `docs/` for necessary keys (Stripe, NextAuth, DB URLs).

* Frontend: `frontend/web/.env.local`
* Backend/AI: `backend/api/.env`

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

* 📖 **[RUNBOOK.md](./RUNBOOK.md)** - System operations, scaling metrics, and SLOs.
* 🚨 **[INCIDENT_RESPONSE.md](./docs/runbooks/incident-response.md)** - Outage mitigation and failover strategies.
* 🧠 **[AI_ORDERING_AGENT.md](https://www.google.com/search?q=./docs/architecture/ai-ordering-agent.md)** - Behavior trees and prompt engineering architecture.
* 🔒 **[SECURITY.md](https://www.google.com/search?q=./SECURITY.md)** - Payload encryption and vulnerability protocols.

---

## 🪪 License

This project is proprietary and licensed under the conditions outlined in [LICENSE.txt](https://www.google.com/search?q=./LICENSE.txt).

---

## Object storage: local now, AWS later

Use the combined base+dev Compose stack: pinned RustFS1.0.6 locally, Amazon S3
as the future production target. No AWS spending or account setup occurs locally.
See [exact commands, data boundaries and IAM example](docs/architecture/object-storage.md).
Older MinIO instructions below/elsewhere are historical, not the active path.

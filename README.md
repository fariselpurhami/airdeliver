airdeliver
we soar in the sky by delivering your orders.

Airdeliver is a fully automated, intelligent eCommerce and Drone Delivery Platform. This monorepo contains the entire production-grade system, architected for enterprise scalability, global readiness, and operational excellence.

✨ Core Features
End-to-End eCommerce Platform: A modern, performant Next.js frontend and a scalable FastAPI backend for a seamless user shopping experience.

Intelligent Drone Control System: A dedicated microservice manages a fleet of drones in real-time using REST and WebSocket APIs, complete with a task queue and compliance layer for no-fly zones.

Global Payment Orchestration: A flexible backend service layer that intelligently routes payments through various gateways (Stripe, PayPal, etc.) based on region, supporting failover and easy expansion.

Advanced Observability: The entire system is instrumented for Prometheus and Grafana, with centralized structured logging and pre-defined SLOs for production monitoring.

Production-Ready Infrastructure: Includes Docker Compose for local development and Kubernetes manifests for auto-scaling production deployments.

Comprehensive Testing: The platform is equipped with unit, integration, and load tests, plus a virtual drone simulator for end-to-end validation without hardware.

🚀 Tech Stack
Monorepo: pnpm Workspaces

Frontend: Next.js, React, TypeScript, Tailwind CSS, Framer Motion, Zustand

Backend: FastAPI (Python), SQLModel, PostgreSQL, Alembic

Real-time Communication: WebSockets

DevOps & Infrastructure: Docker, Kubernetes, Prometheus, Grafana, GitHub Actions

Testing: Pytest (Backend), Jest & React Testing Library (Frontend), Locust (Load Testing)

📦 Monorepo Structure
The project uses a standard apps/ and packages/ structure to maintain a clean separation of concerns.

/airdeliver
├── apps/
│   ├── api/            # Main eCommerce Backend (FastAPI)
│   ├── drone-control/  # Drone Fleet Management Service (FastAPI)
│   └── web/            # Customer-facing Frontend (Next.js)
├── docs/               # High-level documentation (DR, Incident Response)
├── drone-client/       # Python client code for drone hardware
├── drone-simulator/    # Virtual drone fleet for testing
├── infra/              # Infrastructure-as-Code (Kubernetes, Grafana)
├── packages/           # Shared libraries (UI components, configs)
├── README.md           # You are here!
├── RUNBOOK.md          # The primary developer and operations manual
└── SECURITY.md         # The project's security policy
🛠️ Getting Started
Follow these steps to get the entire airdeliver platform running on your local machine.

Prerequisites
Docker & Docker Compose

Node.js v20+ & pnpm v9+

Python v3.11+ & Poetry

Installation
Clone the Repository:

Bash

git clone https://github.com/your-repo/airdeliver.git
cd airdeliver
Install All Dependencies:
This command will install dependencies for all applications and packages in the monorepo.

Bash

pnpm install
poetry install --all-extras
Running the Stack
The simplest way to run the entire application stack (all services + database) is with Docker Compose.

Configure Environment Variables:

Create a .env.local file in apps/web. A minimal setup requires NEXTAUTH_SECRET=your-secret and NEXTAUTH_URL=http://localhost:3000.

The backend .env files will work out-of-the-box with the Docker Compose setup.

Launch with Docker Compose:

Bash

docker-compose up --build
Once started, the services will be available at:

🌐 Frontend: http://localhost:3000

📦 Main API: http://localhost:8000

🚁 Drone Control API: http://localhost:8001

📚 Documentation
This README.md is a high-level overview. For detailed technical and operational information, please refer to the following documents:

Developer Runbook (RUNBOOK.md): The primary guide for setup, testing, deployment, migrations, and SLO targets.

Security Policy (SECURITY.md): Outlines our security measures and how to report vulnerabilities.

: Our strategy for maintaining service availability.

: Procedures for handling critical system incidents.

📄 License
This project is licensed under the MIT License. See the LICENSE file for details.

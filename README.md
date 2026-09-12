# NovaResolve — Autonomous Agentic Customer Resolution Platform

[![Vercel Deployment](https://img.shields.io/badge/Vercel-Live%20Demo%20Ready-000000.svg?style=flat&logo=vercel)](https://novaresolve-agentic-ai.vercel.app)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-336791.svg?style=flat&logo=postgresql)](https://www.postgresql.org)
[![Google Gemini](https://img.shields.io/badge/LLM-Gemini_2.0_Flash-4285F4.svg?style=flat&logo=google)](https://aistudio.google.com)
[![Tests](https://img.shields.io/badge/Tests-136%20Passed%20(100%25)-success.svg?style=flat)](file:///C:/Users/nikhi/OneDrive/Desktop/coding/AGENTIC_AI/backend/tests/)
[![Architecture](https://img.shields.io/badge/Architecture-Autonomous%20Agentic%20Loop-orange.svg?style=flat)](#system-architecture)
[![Repository](https://img.shields.io/badge/GitHub-novaresolve--agentic--ai-181717.svg?style=flat&logo=github)](https://github.com/nikhillakra2007-tech/novaresolve-agentic-ai)

**NovaResolve** is an enterprise-grade Autonomous Agentic AI Customer Resolution Platform built for the e-commerce company **NovaCart**. 

Unlike simple chatbots that generate unverified text, NovaResolve operates as a **closed-loop autonomous system**: it investigates enterprise telemetry, respects deterministic return and risk policies, executes transactional state mutations (atomic stock reservations and payment refunds), dynamically adapts and replans around real-world constraints (such as zero-inventory warehouses), and **independently verifies** that the observed database state matches the customer's goal before resolving a case.

---

## Live Links & Quick Access

- **Live Production App (Vercel)**: [https://novaresolve-agentic-ai.vercel.app](https://novaresolve-agentic-ai.vercel.app)
- **GitHub Repository**: [nikhillakra2007-tech/novaresolve-agentic-ai](https://github.com/nikhillakra2007-tech/novaresolve-agentic-ai)
- **Live Health Status**: [https://novaresolve-agentic-ai.vercel.app/api/health](https://novaresolve-agentic-ai.vercel.app/api/health)
- **Local Dashboard Interface**: [http://127.0.0.1:3000](http://127.0.0.1:3000)
- **Interactive Swagger REST Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc API Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **System Health Endpoint**: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

---

## Visual Showcase & Dashboard Experience

### 1. Autonomous Resolution Command Center
The NovaResolve dashboard gives customer resolution teams real-time visibility into active autonomous investigations, queued cases, and agent telemetry.

![Dashboard Overview](docs/screenshots/dashboard_overview_light.png)

*Key Highlights:*
- **Live Metrics Cards**: Real-time counters for active cases, pending human approvals, escalated disputes, and verified resolutions.
- **Authoritative Telemetry**: Visualizes what the backend actually did—never invents fake agent actions.
- **Filterable Queue**: Real-time sorting and filtering across risk levels (Low, Medium, High) and resolution lifecycles.

---

### 2. Real-Time Execution Trace & Adaptive Replanning
When an agent pursues a resolution, every investigation step, policy evaluation, tool invocation, and replanning pivot is streamed to an audit-grade timeline.

![Execution Trace Timeline](docs/screenshots/execution_trace_timeline.png)

*Key Highlights:*
- **Constraint Detection**: When the primary warehouse has 0 units in stock, the agent marks a `CONSTRAINT_DETECTED` event.
- **Autonomous Replanning**: The agent dynamically triggers `search_alternative_inventory`, discovers eligible fulfillment hubs, and reroutes fulfillment without failing the ticket.
- **Independent State Verification**: Action execution != verified outcome. The `verify_resolution` tool independently validates database parity before marking the case resolved.

---

### 3. Human-in-the-Loop Risk & Approval Gate
NovaResolve enforces strict financial safety bounds. High-risk actions (such as refunds exceeding the $100.00 autonomous threshold) automatically freeze state-changing mutations and wait for supervisor sign-off.

![Human Approval Gate](docs/screenshots/human_approval_gate.png)

*Key Highlights:*
- **Zero Pre-Approval Mutations**: The database remains untouched until explicit human review.
- **Resume Flow**: Approving or rejecting via the UI calls `POST /api/agent/resume`, allowing the agent loop to pick up the staged plan, execute the approved action, and run verification.

---

### 4. Multi-Persona Perspectives & Spotlight Focus Mode
Designed for high-velocity resolution operations with customized role views, dark/light themes, and immersive keyboard-driven focus mode (`F` key).

| Multi-Persona Control Room | Spotlight Focus Mode (Dark Theme) |
| :---: | :---: |
| ![Multi Persona Selector](docs/screenshots/multi_persona_selector.png) | ![Focus Mode Dark](docs/screenshots/focus_mode_dark.png) |
| *Switch dynamically between Resolution Manager, Tier-2 Dispute Specialist, and Customer View.* | *Distraction-free spotlight focus mode dimming background elements during critical investigations.* |

---

### 5. Advanced Mission Control Capabilities

- **Autonomous Supply Chain Re-Routing Matrix**: Real-time visual supply chain tracking showing stockouts at origin hubs (Delhi Hub 0 units) with dynamic spatial rerouting to regional robotic hubs (Jaipur Hub 4 units reserved) and automated priority carrier assignment (`#NE-9821`).
- **Interactive Scrubber & Speed Controls**: Scrub through the agent's 9 reasoning stages with manual step stepping and variable replay speeds (`1x`, `2x`, `4x`).
- **Web Audio API Sound Synthesizer**: Native in-browser acoustic feedback for step execution, spatial rerouting alerts, resolution victory chords, and supervisor gate warnings.
- **Zero-Trust Parity Matrix**: Side-by-side comparative ledger audit verifying Expected State vs Observed DB Truth with cryptographic audit seal validation.
- **Omni Command Palette (<kbd>Ctrl</kbd> + <kbd>K</kbd>)**: Instant fuzzy action and case launcher.
- **60 FPS Confetti Physics Engine**: Pure canvas celebration on verified resolution.

---

## System Architecture

NovaResolve connects user interaction, REST APIs, autonomous reasoning, deterministic tools, and PostgreSQL ACID storage into a single authoritative flow:

```mermaid
flowchart TD
    subgraph UI_Layer["1. Presentation & Control Layer"]
        Customer["Customer / Resolution Manager"]
        Frontend["NovaResolve Modern Dashboard\n(Vanilla ES Modules + Server Proxy :3000)"]
        Customer -->|Interacts with Cases & Approvals| Frontend
    end

    subgraph API_Layer["2. Authoritative REST API (FastAPI :8000)"]
        REST["FastAPI Gateway /api"]
        AgentRoutes["Agent Endpoints\n(/run, /resume, /cases, /trace)"]
        DomainRoutes["Domain Endpoints\n(/refunds, /replacements, /cancellations, /inventory)"]
        Frontend -->|Reverse Proxy / Direct Fetch| REST
        REST --> AgentRoutes
        REST --> DomainRoutes
    end

    subgraph Agent_Core["3. Autonomous Agent Runtime (agents/)"]
        AgentLoop["NovaResolveAgent Runtime Loop\n(Bounded: Max 20 Steps, Max 3 Replans)"]
        StateManager["StateManager\n(Audit Evidence, State Transitions)"]
        DecisionProvider["Decision Provider Interface"]
        LLM["Google Gemini 2.0 Flash\n(Structured Function Calling)"]
        Deterministic["Deterministic Fallback Engine\n(Safety Fallback on Error/Missing Key)"]
        RiskEngine["RiskEvaluator Gate\n($100+ Approval Threshold Enforcement)"]
        Replanner["AgentReplanner\n(Zero-Stock Rerouting & Strategy Pivots)"]

        AgentRoutes --> AgentLoop
        AgentLoop --> StateManager
        AgentLoop --> DecisionProvider
        DecisionProvider -->|Primary| LLM
        DecisionProvider -.->|Fallback| Deterministic
        AgentLoop --> RiskEngine
        AgentLoop --> Replanner
    end

    subgraph Tools_Domain["4. Tool Registry & Domain Services"]
        ToolRegistry["Central Tool Registry\n(13 Sandboxed Typed Tools)"]
        ToolExecutor["ToolExecutor\n(Context: DB Session & Case ID)"]
        
        subgraph Services["Domain Services Layer"]
            CustService["CustomerService"]
            OrdService["OrderService"]
            ShipService["ShipmentService"]
            InvService["InventoryService"]
            PolService["PolicyService"]
            RefService["RefundService (Pessimistic Lock)"]
            RepService["ReplacementService (Atomic Reserve)"]
            CancService["CancellationService (Conflict Check)"]
            VerifService["VerificationService (Independent Audit)"]
        end

        AgentLoop --> ToolExecutor
        ToolExecutor --> ToolRegistry
        ToolRegistry --> Services
    end

    subgraph DB_Layer["5. PostgreSQL Enterprise Storage (:5432)"]
        Postgres[(PostgreSQL 16+\nSchema: 13 Tables, Check Constraints,\nRow-Level Pessimistic Locking)]
        Services -->|SQLAlchemy 2.x ACID Operations| Postgres
    end

    %% Closed Loop Verification & Telemetry
    VerifService -->|Independent Verification Audit| AgentLoop
    AgentLoop -->|Audit Events / Trace Logging| Postgres
    Postgres -.->|Live Telemetry Stream| Frontend
```

---

## Core Capabilities & Cool Features

### 1. Autonomous Investigation & Goal Pursuit
- Given a plain-text customer issue, the agent independently reads customer profiles, inspects order histories, checks carrier delivery telemetry, and identifies the core resolution goal.
- Never relies on client-provided assumptions; pulls authoritative data directly from backend domain services.

### 2. Adaptive Replanning on Constraint
- When attempting a replacement order, if the primary warehouse has 0 units available, the agent:
  1. Detects and logs `CONSTRAINT_DETECTED`.
  2. Enters `REPLANNING` state.
  3. Invokes `search_alternative_inventory` across all active enterprise hubs.
  4. Selects an alternative warehouse (e.g. Reno West Warehouse with 15 units available).
  5. Executes fulfillment from the alternative warehouse and verifies the stock reservation.

### 3. Financial Safety & Human Approval Gate
- Automatically computes transaction risk based on amount, customer tier, and policy constraints.
- Any refund exceeding **$100.00** triggers `APPROVAL_REQUIRED`.
- The agent halts execution *before* any state-changing mutation, serializing state into `awaiting_approval`.
- Once a human supervisor clicks **Approve** in the dashboard, the agent automatically resumes, executes the refund, and independently audits the database.

### 4. Independent State Verification
- **Action Success != Verified Resolution**: Just because an API returns `200 OK` doesn't mean the customer's issue was resolved correctly.
- NovaResolve invokes an independent `VerificationService` that queries PostgreSQL to verify:
  - Refund record exists with exact expected amount and status `completed`.
  - Replacement record exists with matching product ID, quantity, and reserved stock.
  - If a state discrepancy is detected (e.g. simulated $79.99 refund on $159.98 order), verification fails and the case is flagged.

### 5. Multi-Persona Experience
- **Resolution Manager**: High-level operational overview, approval queues, aggregate velocity metrics.
- **Dispute Specialist**: Priority queue of escalated cases, conflict traces, and carrier mismatch disputes.
- **Customer View**: Transparent real-time progress tracker explaining exactly what the agent is investigating and fulfilling.

### 6. Modern Scroll & Focus Aesthetics
- Built with custom dark/light themes, smooth micro-transitions, responsive layouts, and a dedicated **Spotlight Focus Mode** (`F` key) for distraction-free case handling.

---

## Live Demo Walkthrough

The repository includes 10 pre-seeded, deterministic scenarios (`db/seed/scenarios.py`) demonstrating autonomous agent behavior:

### Scenario 1: Normal Instant Resolution (Alice)
- **Goal**: Customer received defective headphones ($45.00); requests direct refund.
- **Flow**: `get_customer` → `get_order` → `get_shipment` → `evaluate_policy` (allowed, low risk) → `create_refund` → `verify_resolution` → **RESOLVED**.

### Scenario 2: Adaptive Replacement & Alternate Warehouse (Bob) — *Primary Demo*
- **Goal**: Customer's monitor arrived broken; requests replacement.
- **Primary Fulfillment Hub**: Dallas Central Warehouse has **0 units**.
- **Agent Adaptation**:
  1. Agent calls `check_inventory` for Dallas → `available_quantity: 0`.
  2. Agent logs `CONSTRAINT_DETECTED` and enters `REPLANNING`.
  3. Agent calls `search_alternative_inventory` → discovers Reno West Warehouse has **15 units**.
  4. Agent calls `create_replacement` routing to Reno West Warehouse.
  5. `verify_resolution` confirms replacement record and inventory reservation.
  6. Case marked **RESOLVED**.

### Scenario 3: High-Risk Refund with Human Approval Gate (Diana)
- **Goal**: High-value smart projector ($520.00) return requested.
- **Flow**: Policy evaluation flags `requires_approval: true` (amount exceeds $100.00 threshold) → Case pauses in `awaiting_approval` status (zero DB mutations) → Supervisor reviews case in dashboard and clicks **Approve** → Agent resumes via `/api/agent/resume` → `create_refund` executes → `verify_resolution` confirms → Case marked **RESOLVED**.

### Scenario 4: Policy Denial & Shipped Cancellation Conflict (Hannah)
- **Goal**: Customer requests cancellation on an order already dispatched with UPS tracking.
- **Flow**: Agent calls `cancel_order` → Backend rejects with `409 Conflict (OrderStateConflictError)` → Agent avoids blind retry loops, logs constraint, and guides customer to return workflow upon delivery.

---

## REST API Endpoints Reference

### Agent Runtime Endpoints
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/agent/cases` | Lists all resolution cases with customer, order, and telemetry details |
| `GET` | `/api/agent/cases/{case_id}` | Retrieves specific case details and current resolution status |
| `GET` | `/api/agent/case/{case_id}/trace` | Retrieves full audit event execution trace for a case |
| `POST` | `/api/agent/run` | Triggers the autonomous agent runtime on a customer case |
| `POST` | `/api/agent/resume` | Resumes an `awaiting_approval` case after human supervisor review |

### Information & Read Services
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | PostgreSQL connectivity, query latency, and connection pool status |
| `GET` | `/api/customers/{customer_id}` | Fetch customer profile by UUID |
| `GET` | `/api/customers/by-email/{email}` | Fetch customer profile by email |
| `GET` | `/api/orders/{order_id}` | Fetch order with items and customer ownership |
| `GET` | `/api/shipments/{order_id}` | Fetch shipment tracking, carrier, and dynamic delivery status |
| `GET` | `/api/inventory/{product_id}/{warehouse_id}` | Exact stock check (observable zero-stock) |
| `GET` | `/api/inventory/{product_id}/alternatives` | Discover active alternative warehouses with available stock |

### Policy & State-Changing Resolution Services
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/policies/evaluate` | Pure policy evaluation (zero mutation) |
| `POST` | `/api/refunds` | Process transactional refund (pessimistic lock, threshold gate) |
| `POST` | `/api/replacements` | Create replacement order (atomic stock reservation, 409 if 0 stock) |
| `POST` | `/api/cancellations` | Cancel order (409 conflict if already in transit) |

---

## Local Setup Runbook

### 1. Prerequisites
- **Python 3.12+**
- **Node.js 18+**
- **PostgreSQL 16+** running locally on port 5432

### 2. Virtual Environment & Dependencies
```powershell
# Create and activate Python virtual environment
python -m venv backend/.venv
.\backend\.venv\Scripts\Activate.ps1

# Install backend dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file in the root directory (or in `backend/`):
```ini
PROJECT_NAME="NovaResolve"
ENVIRONMENT="development"
DEBUG=True
DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/novacart"
API_V1_STR="/api"
PORT=8000
HOST="127.0.0.1"

# Google Gemini LLM Configuration (Optional: fallback to deterministic if empty)
LLM_PROVIDER="gemini"
LLM_MODEL="gemini-2.0-flash"
GEMINI_API_KEY="your_actual_gemini_api_key_here"
LLM_FALLBACK_TO_DETERMINISTIC=True
LLM_TIMEOUT_SECONDS=15
```

### 4. Initialize Database & Seed Deterministic Scenarios
```powershell
# In PostgreSQL, create the database
psql -U postgres -h localhost -c "CREATE DATABASE novacart;"

# Apply Alembic schema migrations
$env:PYTHONPATH="."
.\backend\.venv\Scripts\alembic.exe upgrade head

# Seed synthetic data and 10 agentic scenarios
python -m db.seed.seed_data
```

### 5. Running Backend & Frontend

**Terminal 1 — Backend FastAPI Service:**
```powershell
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
*Backend runs at: [http://127.0.0.1:8000](http://127.0.0.1:8000) (Swagger docs at `/docs`)*

**Terminal 2 — Frontend Application:**
```powershell
cd frontend
node server.mjs
```
*Frontend runs at: [http://127.0.0.1:3000](http://127.0.0.1:3000) (transparently reverse-proxies `/api/*` to `:8000`)*

---

## Running Automated Tests

NovaResolve includes a test suite with **136 automated tests** covering all domain models, services, tools, agent loop, LLM decision making, and end-to-end integration scenarios:

```powershell
# Run the complete test suite
$env:PYTHONPATH="."
pytest backend/tests/ -v
```

### Test Suite Breakdown
| Test Module | Coverage Area | Tests | Status |
|---|---|:---:|:---:|
| `test_health.py` | PostgreSQL connection latency & pool health | 3 | **PASS** |
| `test_models.py` | 13 SQLAlchemy models & check constraints | 8 | **PASS** |
| `test_seed_scenarios.py` | 10 pre-seeded scenario state validations | 10 | **PASS** |
| `test_services_read.py` | Customer, Order, Shipment, Inventory read services | 6 | **PASS** |
| `test_services_resolution.py` | Transactional Refunds, Replacements, Cancellations | 11 | **PASS** |
| `test_api_endpoints.py` | FastAPI REST HTTP status mappings (200, 201, 400, 404, 409) | 7 | **PASS** |
| `test_agent_tools.py` | 13 Sandboxed typed tool contracts & schema checks | 48 | **PASS** |
| `test_agent_runtime.py` | Deterministic agent loop, bounds, replanning, verification | 15 | **PASS** |
| `test_agent_llm.py` | LLM decision provider, function calling, fallback, safety gates | 22 | **PASS** |
| `test_e2e_integration.py` | 6 Mandatory End-to-End integration scenarios | 6 | **PASS** |
| **TOTAL** | **Full System Verification** | **136** | **100% PASS** |

---

## Deployment Guide

### Deploying to Production (e.g. Render / Railway / Docker)

1. **Database**: Provision a managed PostgreSQL instance (e.g. Supabase, Neon, AWS RDS, Railway Postgres).
2. **Environment Variables**:
   ```env
   DATABASE_URL=postgresql+psycopg://<user>:<password>@<host>:5432/<dbname>
   GEMINI_API_KEY=<your_production_gemini_key>
   ENVIRONMENT=production
   DEBUG=False
   ```
3. **Backend Service Command**:
   ```bash
   alembic upgrade head && python -m db.seed.seed_data && uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
   ```
4. **Frontend Static/Proxy Service**:
   ```bash
   cd frontend && node server.mjs
   ```

---

## Project Structure

```
novaresolve-agentic-ai/
├── api/                         # Vercel serverless functions (/health, /agent/cases, /agent/run, etc.)
├── backend/
│   ├── app/
│   │   ├── api/routes/          # FastAPI route controllers (/agent, /health, /refunds, etc.)
│   │   ├── core/                # App configuration, security, domain exceptions
│   │   ├── db/models/           # 13 SQLAlchemy 2.0 ORM models (ACID & row locks)
│   │   ├── schemas/             # Typed Pydantic v2 validation contracts
│   │   └── services/            # Pure domain services (Refund, Replacement, Policy, etc.)
│   └── tests/                   # 136 automated Pytest tests
├── agents/
│   ├── planning/                # DecisionProvider, LLMDecisionProvider, DeterministicProvider
│   │   └── llm/                 # GeminiClient, structured function calling, prompt templates
│   ├── replanning/              # AgentReplanner (zero-stock & constraint adaptation)
│   ├── risk/                    # RiskEvaluator (approval threshold gates)
│   ├── runtime/                 # NovaResolveAgent execution loop & limits
│   ├── state/                   # AgentState, StateManager, AgentObservation, audit trail
│   └── tools/                   # Central TOOL_REGISTRY & 13 sandboxed tools
├── frontend/
│   ├── components/
│   │   ├── navigation/          # Sidebar & routing
│   │   ├── users/               # Multi-persona control room & preference modals
│   │   ├── metrics/             # Live KPI counter cards
│   │   ├── case-panel/          # Authoritative agent focus card & fulfillment route map
│   │   ├── verification/        # Step-by-step execution trace & verification views
│   │   ├── approvals/           # Human oversight review cards & policy safeguard panel
│   │   └── case-queue/          # Filterable resolution case table
│   ├── styles/                  # Clean global design system & keyframe animations
│   ├── app.js                   # Application state machine & live REST API connector
│   └── server.mjs               # Zero-dependency ES module server & /api reverse proxy
├── db/
│   ├── migrations/              # Alembic database migration revisions
│   └── seed/                    # Deterministic seed generator & 10 agentic scenarios
├── docs/screenshots/            # Presentation-grade screenshots of the live system
├── GEMINI.md                    # Project rules & persistent frontend standards
└── README.md                    # System documentation & architectural reference
```

---

## License

Developed for the **NovaResolve Agentic AI Hackathon Project** by Nikhil Lakra. All rights reserved.

# NovaResolve — Agentic AI Customer Resolution Platform

**NovaResolve** is an autonomous agentic AI customer-resolution platform built for a simulated e-commerce enterprise called **NovaCart**.

The system is designed to investigate customer issues, inspect enterprise data, evaluate business and risk constraints, execute simulated state-changing resolutions (refunds, replacements, cancellations), adapt when actions are blocked or fail, and independently verify the final outcome.

---

## Current Architecture & Scope

This repository contains the **Phase 1 Backend & Database Foundation**:
- **Application Framework**: Python 3.12, FastAPI (modular routing)
- **Database**: PostgreSQL 18.x directly (UUID PKs, check constraints, foreign keys, performance indexes)
- **ORM & Sessions**: SQLAlchemy 2.x declarative models and scoped session dependency
- **Database Migrations**: Alembic (`0001_initial_schema`)
- **Configuration**: Pydantic Settings loaded from `.env`
- **Synthetic Domain Data**: Deterministic seeding of 60 customers, 26 products, 4 warehouses, 220 orders, shipments, policies, and **10 explicit agentic scenarios**.

> [!NOTE]
> **Phase Boundaries**: The Agent Runtime (LLM loop, planning, tools) and the Next.js Frontend are intentionally separate future phases. This foundation establishes the clean, typed data and service boundaries they require.

---

## Directory Structure

```
novaresolve-agentic-ai/
├── backend/
│   ├── .env                       # Local environment variables
│   ├── requirements.txt           # Pinned Python dependencies
│   ├── app/
│   │   ├── main.py                # FastAPI entrypoint and root endpoint
│   │   ├── api/
│   │   │   └── routes/
│   │   │       └── health.py      # GET /api/health with DB latency & pool stats
│   │   ├── core/
│   │   │   └── config.py          # Pydantic Settings (PROJECT_NAME="NovaResolve")
│   │   ├── db/
│   │   │   ├── base.py            # DeclarativeBase, UUIDPrimaryKeyMixin, TimestampMixin
│   │   │   ├── session.py         # Engine, sessionmaker, get_db, check_db_connection
│   │   │   └── models/            # Separated SQLAlchemy 2.0 domain models (13 tables)
│   │   │       ├── customer.py
│   │   │       ├── product.py
│   │   │       ├── warehouse.py
│   │   │       ├── inventory.py
│   │   │       ├── order.py       # Order and OrderItem
│   │   │       ├── shipment.py
│   │   │       ├── policy.py
│   │   │       ├── case.py        # Case (Agent State persistence)
│   │   │       ├── refund.py
│   │   │       ├── replacement.py
│   │   │       ├── cancellation.py
│   │   │       └── agent_event.py # AgentEvent (Observable event log)
│   │   ├── schemas/
│   │   │   └── health.py          # Pydantic API response schemas
│   │   └── services/              # Future domain service layer boundary
│   └── tests/                     # Automated Pytest test suite
│       ├── conftest.py
│       ├── test_health.py
│       ├── test_models.py
│       └── test_seed_scenarios.py
├── db/
│   ├── migrations/
│   │   ├── 001_initial_schema.sql # Reference raw SQL bootstrap migration
│   │   ├── env.py                 # Alembic environment linked to Base.metadata
│   │   └── versions/
│   │       └── 0001_initial_schema.py # Native Alembic migration
│   └── seed/
│       ├── scenarios.py           # Definitions for 10 deliberate agentic scenarios
│       └── seed_data.py           # Deterministic database seeding script
├── agents/                        # Future agent runtime & planner modules
├── frontend/                      # Future Next.js resolution dashboard
├── alembic.ini                    # Alembic configuration
├── requirements.txt               # Root dependency entrypoint
├── .env.example                   # Example environment file
└── README.md
```

---

## Local Setup Runbook

### 1. Prerequisites
- Python 3.12+
- PostgreSQL 16+ running locally on port 5432

### 2. Virtual Environment & Dependencies
```powershell
# Create virtual environment inside backend/
python -m venv backend/.venv

# Activate virtual environment
# Windows PowerShell:
.\backend\.venv\Scripts\Activate.ps1
# Linux / macOS:
# source backend/.venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file in `backend/` (or copy from `.env.example`):
```ini
PROJECT_NAME="NovaResolve"
ENVIRONMENT="development"
DEBUG=True
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/novacart
API_V1_STR="/api"
PORT=8000
HOST="127.0.0.1"
```

### 4. Create Database & Apply Migrations
```powershell
# In PostgreSQL, create the novacart database
psql -U postgres -h localhost -c "CREATE DATABASE novacart;"

# Apply the native Alembic migrations
$env:PYTHONPATH="."
.\backend\.venv\Scripts\alembic.exe upgrade head
```

### 5. Seed Synthetic Data & Scenarios
```powershell
# Run the deterministic seed script
python -m db.seed.seed_data
```

This generates:
- **60 Customers** (10 Scenario Customers + 50 Synthetic Customers)
- **26 Products** across Audio, Electronics, Home, Wearables, and Accessories
- **4 Warehouses** (Dallas Central, Atlanta East, Reno West, Chicago North)
- **104 Inventory Records** with scenario-specific stock distributions
- **220 Orders & 427 Order Items**
- **140 Shipments** with carrier tracking
- **6 Resolution Policies** with JSONB condition rules
- **10 Pre-seeded Agentic Scenarios** with Cases, Events, Refunds, Replacements, and Cancellations

---

## Running the Application

Start the FastAPI application:
```powershell
.\backend\.venv\Scripts\uvicorn.exe backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Verify Endpoints
- **Root Endpoint**: `GET http://127.0.0.1:8000/`
  ```json
  {
    "service": "NovaResolve API",
    "status": "running"
  }
  ```
- **Health Endpoint**: `GET http://127.0.0.1:8000/api/health`
  ```json
  {
    "service": "NovaResolve API",
    "status": "healthy",
    "environment": "development",
    "version": "1.0.0",
    "database": {
      "status": "connected",
      "latency_ms": 110.28,
      "pool": {
        "size": 10,
        "checkedin": 0,
        "checkedout": 1,
        "overflow": -9
      }
    }
  }
  ```
- **Interactive OpenAPI Documentation**: `http://127.0.0.1:8000/docs`

---

## Running Automated Tests

Run the complete Pytest test suite:
```powershell
$env:PYTHONPATH="."
.\backend\.venv\Scripts\pytest.exe backend/tests -v
```

Tests verify:
- Configuration loading and `NovaResolve API` service status
- Live PostgreSQL connectivity, latency measurement, and degraded state handling
- All 13 SQLAlchemy models registered in metadata
- Foreign keys and cascade delete behaviors (e.g. order item cascade)
- Check constraints (negative price rejection, reserved quantity > total quantity rejection, invalid customer status)
- Automatic `created_at` timestamps on products and warehouses
- PostgreSQL `updated_at` trigger updating inventory, policies, and cases
- Reusable `get_db()` session lifecycle
- All 10 deliberate agentic failure and resolution scenarios

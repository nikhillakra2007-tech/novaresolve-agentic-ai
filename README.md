# NovaResolve — Agentic AI Customer Resolution Platform

**NovaResolve** is an autonomous agentic AI customer-resolution platform built for a simulated e-commerce enterprise called **NovaCart**.

The system is designed to investigate customer issues, inspect enterprise data, evaluate business and risk constraints, execute simulated state-changing resolutions (refunds, replacements, cancellations), adapt when actions are blocked or fail, and independently verify the final outcome.

---

## Current Architecture & Scope

This repository contains **Phase 1 (Database & Backend Foundation)**, **Phase 2 (Domain Services & REST API Layer)**, and **Phase 3 (Agent Tools & Capability Layer)**:
- **Application Framework**: Python 3.12, FastAPI (modular routing under `/api`)
- **Database**: PostgreSQL 18.x directly (UUID PKs, check constraints, foreign keys, performance indexes)
- **ORM & Sessions**: SQLAlchemy 2.x declarative models and scoped session dependency
- **Database Migrations**: Alembic (`0001_initial_schema`, `0002_add_replacement_quantity`)
- **Domain Services**:
  1. `CustomerService`: ID/email lookups, active requester validations
  2. `OrderService`: Order item retrieval, customer ownership validations
  3. `ShipmentService`: Carrier tracking events, dynamic `is_delayed` calculation
  4. `InventoryService`: Warehouse stock checks (observable zero-stock), alternative active warehouse discovery
  5. `PolicyService`: Priority rule evaluator, threshold checks, approval detection, `allowed_reasons` enforcement
  6. `RefundService`: Transactional refund execution, balance validation, pessimistic row lock, $100 supervisor threshold
  7. `ReplacementService`: Pessimistic locking (`with_for_update`), quantity persistence, atomic stock reservation
  8. `CancellationService`: Fulfillment state inspection, shipment conflict enforcement
  9. `CaseService`: Safe case lifecycle updates, plan tracking, sanitized agent audit event logging
  10. `VerificationService`: Independent post-resolution state verification across resolutions, orders, and inventory
- **Agent Tool Layer (`agents/tools/`)**:
  - 13 typed, deterministic capabilities organized into Observation, Decision, Action, and Case Support categories.
  - Standardized `ToolResult` envelope with preserved domain error statuses.
  - Central `TOOL_REGISTRY` with strict safety boundaries (blocks raw SQL, eval, and arbitrary execution).
- **Synthetic Domain Data**: Deterministic seeding of 60 customers, 26 products, 4 warehouses, 220 orders, shipments, policies, and **10 explicit agentic scenarios**.

> [!NOTE]
> **Phase Boundaries**: The Agent Runtime (LLM loop, planning, ReAct agents) and the Next.js Frontend are intentionally separate future phases (Phase 4 and Phase 5). Phase 3 establishes the controlled capability interface that the future agent will invoke.

---

## REST API Endpoints

### 1. Information & Read Services
| Method | Endpoint | Description | HTTP Status |
|---|---|---|---|
| `GET` | `/api/health` | PostgreSQL connectivity, latency, and pool stats | 200 / 503 |
| `GET` | `/api/customers/{customer_id}` | Fetch customer profile by UUID | 200 / 404 |
| `GET` | `/api/customers/by-email/{email}` | Fetch customer profile by email | 200 / 404 |
| `GET` | `/api/orders/{order_id}` | Fetch order with items (optional `customer_id` check) | 200 / 404 |
| `GET` | `/api/shipments/{order_id}` | Fetch shipment tracking & dynamic delay flag | 200 / 404 |
| `GET` | `/api/inventory/{product_id}/{warehouse_id}` | Exact stock check (preserves zero-stock observation) | 200 / 404 |
| `GET` | `/api/inventory/{product_id}/alternatives` | Discover active alternative warehouses with stock | 200 / 404 |

### 2. Decision Service
| Method | Endpoint | Description | HTTP Status |
|---|---|---|---|
| `POST` | `/api/policies/evaluate` | Evaluate policy constraints (pure decision, no mutation) | 200 / 400 |

### 3. State-Changing Resolution Services
| Method | Endpoint | Description | HTTP Status |
|---|---|---|---|
| `POST` | `/api/refunds` | Process transactional refund ($100 approval check, balance limit) | 201 / 400 / 403 / 404 |
| `POST` | `/api/replacements` | Create replacement order (row lock, stock reservation, 409 if out of stock) | 201 / 400 / 403 / 409 |
| `POST` | `/api/cancellations` | Cancel order (409 conflict if already shipped or in-transit) | 200 / 400 / 403 / 409 |

---

## Directory Structure

```
novaresolve-agentic-ai/
├── backend/
│   ├── .env                       # Local environment variables
│   ├── requirements.txt           # Pinned Python dependencies
│   ├── app/
│   │   ├── main.py                # FastAPI entrypoint, exception handlers & router mounting
│   │   ├── api/
│   │   │   └── routes/
│   │   │       ├── health.py      # GET /api/health
│   │   │       ├── customers.py   # GET /api/customers/{id}, /by-email/{email}
│   │   │       ├── orders.py      # GET /api/orders/{order_id}
│   │   │       ├── shipments.py   # GET /api/shipments/{order_id}
│   │   │       ├── inventory.py   # GET /api/inventory/{prod}/{wh}, /alternatives
│   │   │       ├── policies.py    # POST /api/policies/evaluate
│   │   │       └── resolutions.py # POST /api/refunds, /replacements, /cancellations
│   │   ├── core/
│   │   │   ├── config.py          # Pydantic Settings
│   │   │   └── exceptions.py      # Domain exceptions (ResourceNotFound, Conflict, etc.)
│   │   ├── db/
│   │   │   ├── base.py            # DeclarativeBase, UUIDPrimaryKeyMixin, TimestampMixin
│   │   │   ├── session.py         # Engine, sessionmaker, get_db, check_db_connection
│   │   │   └── models/            # Separated SQLAlchemy 2.0 domain models (13 tables)
│   │   ├── schemas/               # Strongly typed Pydantic v2 schemas
│   │   │   ├── health.py
│   │   │   ├── customer.py
│   │   │   ├── order.py
│   │   │   ├── shipment.py
│   │   │   ├── inventory.py
│   │   │   ├── policy.py
│   │   │   └── resolution.py
│   │   └── services/              # Pure domain services
│   │       ├── customer_service.py
│   │       ├── order_service.py
│   │       ├── shipment_service.py
│   │       ├── inventory_service.py
│   │       ├── policy_service.py
│   │       ├── refund_service.py
│   │       ├── replacement_service.py
│   │       ├── cancellation_service.py
│   │       ├── case_service.py
│   │       └── verification_service.py
│   └── tests/                     # Automated Pytest test suite (88 passing tests)
│       ├── conftest.py
│       ├── test_health.py
│       ├── test_models.py
│       ├── test_seed_scenarios.py
│       ├── test_services_read.py
│       ├── test_services_resolution.py
│       ├── test_api_endpoints.py
│       └── test_agent_tools.py
├── db/
│   ├── migrations/
│   │   ├── 001_initial_schema.sql
│   │   ├── 002_add_replacement_quantity.sql
│   │   ├── env.py
│   │   └── versions/
│   │       ├── 0001_initial_schema.py
│   │       └── 0002_add_replacement_quantity.py
│   └── seed/
│       ├── scenarios.py           # Definitions for 10 deliberate agentic scenarios
│       └── seed_data.py           # Deterministic database seeding script
├── agents/                        # Agent capability layer (Phase 3)
│   ├── __init__.py
│   ├── README.md
│   └── tools/
│       ├── __init__.py
│       ├── base.py                # BaseTool, ToolResult, ToolContext, ToolResultStatus
│       ├── customer_tools.py      # get_customer
│       ├── order_tools.py         # get_order
│       ├── shipment_tools.py      # get_shipment
│       ├── inventory_tools.py     # check_inventory, search_alternative_inventory
│       ├── policy_tools.py        # evaluate_policy
│       ├── resolution_tools.py    # create_refund, create_replacement, cancel_order
│       ├── case_tools.py          # get_case_state, persist_case_state, log_agent_event, verify_resolution
│       └── registry.py            # TOOL_REGISTRY & execution boundary
├── frontend/                      # Future Next.js resolution dashboard (scroll-craft)
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
.\backend\.venv\Scripts\Activate.ps1

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

---

## Running the Application

Start the FastAPI application:
```powershell
.\backend\.venv\Scripts\uvicorn.exe backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

- **Interactive Swagger Docs**: `http://127.0.0.1:8000/docs`
- **ReDoc Documentation**: `http://127.0.0.1:8000/redoc`

---

## Running Automated Tests

Run the complete Pytest test suite (40 tests):
```powershell
$env:PYTHONPATH="."
.\backend\.venv\Scripts\pytest.exe backend/tests -v
```

All 40 tests execute in < 2 seconds and verify:
- System health and PostgreSQL connectivity latency
- All 13 SQLAlchemy models and check constraints
- Seed scenario integrity across 10 deliberate customer problems
- Customer, Order, Shipment, and Inventory read services
- Zero-stock inventory observable constraint preservation
- Alternative warehouse discovery
- Priority-based policy evaluation
- Transactional state-changing resolutions (Refunds, Replacements, Cancellations)
- Concurrent stock reservation with pessimistic locking
- FastAPI REST endpoints HTTP status code mappings (200, 201, 400, 403, 404, 409)

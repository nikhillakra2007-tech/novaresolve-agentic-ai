# NovaResolve — Agent Tools & Capability Layer (Phase 3)

Phase 3 implements the typed, controlled **Agent Tool / Capability Layer** for NovaResolve.

The tool layer exposes the deterministic domain capabilities implemented in Phase 2 to the future autonomous agent runtime.

> [!IMPORTANT]
> **Phase 3 Boundary**:
> Phase 3 provides capabilities ("What can the agent do?").
> It does **NOT** include LLM reasoning, autonomous loops, ReAct agents, LangChain/LangGraph, or frontend code. Those belong to later phases.

---

## 1. Architectural Principle

The future agent interacts with NovaCart exclusively through controlled tools rather than unrestricted database access:

```text
Future Agent / Intent
        ↓
    Agent Tool
        ↓
Phase 2 Domain Service
        ↓
SQLAlchemy ORM
        ↓
    PostgreSQL
        ↓
Structured ToolResult
```

### Prohibited Patterns:
- ❌ `Agent → Raw SQL → Database`
- ❌ `Agent → Tool → Arbitrary SQL / PyExec`
- ❌ `Agent → Tool → Duplicated Business Logic`

### Enforced Pattern:
- ✅ `Agent → Tool → Domain Service → Database`

---

## 2. Tool Result & Error Contract

All tools return a structured, predictable envelope:

```python
class ToolResult(BaseModel):
    success: bool
    tool_name: str
    data: Optional[Any] = None
    error: Optional[ToolError] = None
    status: ToolResultStatus
    message: str
```

Domain errors are preserved with explicit semantic statuses rather than swallowed:
- `SUCCESS`
- `FAILED`
- `BLOCKED`
- `NOT_FOUND`
- `INVALID`
- `POLICY_DENIED`
- `INSUFFICIENT_INVENTORY`
- `DUPLICATE`
- `APPROVAL_REQUIRED`
- `CONFLICT`
- `CUSTOMER_BLOCKED`
- `CUSTOMER_INACTIVE`

---

## 3. Tool Categories & The 13 Available Tools

### A. Observation Tools
Used to obtain facts from the enterprise without mutation:
1. `get_customer`: Retrieve customer profile and active/blocked flags.
2. `get_order`: Retrieve order details, line items, and ownership validation.
3. `get_shipment`: Retrieve carrier tracking, fulfillment status, and delay indicators.
4. `check_inventory`: Check product availability at a specific warehouse. Returns 0 available stock as an observable fact without auto-rerouting.
5. `search_alternative_inventory`: Discover active alternative warehouses with sufficient available stock. Does not make routing decisions.
6. `get_case_state`: Retrieve current lifecycle state, plan, progress step, and resolution status for a case.

### B. Decision / Policy Tools
Used to evaluate constraints and business policies without mutating state:
7. `evaluate_policy`: Evaluates active policies against issue types, actions, order age, shipment state, refund amounts, and allowed reasons.

### C. State-Changing Action Tools
Request business state mutations through Phase 2 transactional services:
8. `create_refund`: Transactional refund execution with row locking, balance checks, policy enforcement, and $100 approval threshold.
9. `create_replacement`: Transactional replacement creation with order item verification, policy check, and atomic inventory reservation.
10. `cancel_order`: Order cancellation with state conflict enforcement (blocks already shipped/in-transit/delivered orders).

### D. Case, Event & Verification Support Tools
Support persistent execution state, event traceability, and independent verification:
11. `persist_case_state`: Safely update allowed lifecycle and plan fields (`status`, `current_plan`, `current_step`, `resolution_type`, `resolution_status`, `risk_level`, `requires_approval`).
12. `log_agent_event`: Persist an observable audit event in `agent_events` for tracing.
13. `verify_resolution`: Independently verify that the executed resolution is consistent across case records, resolution entities, orders, and warehouse inventory.

---

## 4. Tool Registry

All authorized tools are registered in a central registry:

```python
from agents.tools import TOOL_REGISTRY, ToolContext, execute_tool

ctx = ToolContext(db=db_session, case_id=case_id)
result = execute_tool("check_inventory", ctx, product_id=pid, warehouse_id=wid)
```

The registry disallows arbitrary Python functions, raw SQL execution (`execute_sql`, `raw_sql`), and unregistered capabilities.

---

## 5. Package Structure

```text
agents/
├── __init__.py
├── README.md
└── tools/
    ├── __init__.py
    ├── base.py                 # ToolResult, ToolContext, BaseTool, ToolResultStatus
    ├── customer_tools.py       # get_customer
    ├── order_tools.py          # get_order
    ├── shipment_tools.py       # get_shipment
    ├── inventory_tools.py      # check_inventory, search_alternative_inventory
    ├── policy_tools.py         # evaluate_policy
    ├── resolution_tools.py     # create_refund, create_replacement, cancel_order
    ├── case_tools.py           # get_case_state, persist_case_state, log_agent_event, verify_resolution
    └── registry.py             # ToolRegistry and tool execution boundary
```

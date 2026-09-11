# NovaCart — Agent Architecture Boundaries

This directory is reserved for future agent modules as part of the Tech Zephyr 4.0 Agentic AI Hackathon.

## Architecture Guidelines (Strict Spec Kit)
As mandated by the NovaCart architecture specification, do **NOT** create giant files (e.g. do NOT create a monolithic `agent.py`). When implementing the agentic subsystem, split responsibilities across focused modules:

```
agents/
├── runtime/           # Execution engine and agent loop orchestration
├── planning/          # Plan generation, step decomposition, and goal tracking
├── state/             # Case state management, persistence, and transitions
├── tools/             # Read tools, decision support tools, and mutation tools
│   ├── read/          # get_customer, get_order, get_shipment, check_inventory, check_policy
│   ├── decision/      # calculate_refund, search_alternative_inventory
│   └── mutation/      # create_refund, create_replacement, cancel_order
├── risk/              # Risk assessment engine (low / medium / high autonomy)
├── verification/      # verify_resolution and post-execution state sanity checks
└── replanning/        # Constraint detection and adaptive replanning recovery
```

## Security & Safety Rules
1. **No Direct SQL Execution**: The agent must never execute unrestricted raw SQL. All data access must pass through backend services and typed schemas.
2. **Deterministic Tool Boundaries**: Every state change (refund, replacement, cancellation) must generate an observable `AgentEvent` in the database.
3. **Approval Gates**: High-risk operations (e.g., refunds exceeding threshold or edge cases) must halt for human review before execution.

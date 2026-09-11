# NovaCart — Frontend Architecture Boundaries

This directory is reserved for the future Next.js application powering the customer resolution portal and agent observability dashboard.

## Architecture Guidelines (Strict Spec Kit)
As mandated by the NovaCart architecture specification, avoid bloated single-file pages and monolithic component files. Modularize by feature:

```
frontend/
├── app/               # Next.js App Router (pages and layouts)
│   ├── layout.tsx
│   ├── page.tsx
│   ├── cases/
│   ├── dashboard/
│   └── approvals/
├── components/        # Reusable UI components (buttons, modals, tables, badges)
├── features/          # Domain-specific feature modules
│   ├── cases/         # Case details, resolution workflow, timeline
│   ├── agent-trace/   # Live event timeline, tool calls, JSON inspector
│   ├── approvals/     # Supervisor queue, approval / rejection actions
│   └── customer/      # Customer profile and order lookup
├── hooks/             # Custom React hooks (e.g. useCase, useHealthCheck)
└── lib/               # API clients, formatting utilities, and types
```

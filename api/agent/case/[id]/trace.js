// Vercel Serverless Function: GET /api/agent/case/[id]/trace

const TRACES = {
  "sc-002-bob": [
    {
      id: "tr-201",
      event_type: "STEP_START",
      tool_name: "get_order",
      status: "success",
      message: "Fetching order details for ord-002-dallas (Product: UltraSharp 4K Monitor).",
      created_at: new Date(Date.now() - 120000).toISOString()
    },
    {
      id: "tr-202",
      event_type: "TOOL_CALL",
      tool_name: "check_inventory",
      status: "success",
      message: "Checking inventory at primary warehouse: Dallas Central Warehouse (quantity: 0).",
      created_at: new Date(Date.now() - 100000).toISOString()
    },
    {
      id: "tr-203",
      event_type: "CONSTRAINT_DETECTED",
      tool_name: "check_inventory",
      status: "warning",
      message: "Primary warehouse has 0 units available. Stock exhaustion constraint detected.",
      created_at: new Date(Date.now() - 85000).toISOString()
    },
    {
      id: "tr-204",
      event_type: "STATE_TRANSITION",
      tool_name: null,
      status: "info",
      message: "Agent transitioned from EXECUTING to REPLANNING. Initiating multi-hub discovery.",
      created_at: new Date(Date.now() - 70000).toISOString()
    },
    {
      id: "tr-205",
      event_type: "TOOL_CALL",
      tool_name: "search_alternative_inventory",
      status: "success",
      message: "Discovered available stock: Reno West Warehouse (15 units available, SLA: 2 days).",
      created_at: new Date(Date.now() - 50000).toISOString()
    },
    {
      id: "tr-206",
      event_type: "TOOL_CALL",
      tool_name: "create_replacement",
      status: "success",
      message: "Created replacement order rep-99201 routing fulfillment to Reno West Warehouse.",
      created_at: new Date(Date.now() - 30000).toISOString()
    },
    {
      id: "tr-207",
      event_type: "VERIFICATION",
      tool_name: "verify_resolution",
      status: "success",
      message: "Independent verification confirms inventory reservation and order parity in PostgreSQL.",
      created_at: new Date(Date.now() - 10000).toISOString()
    }
  ],
  "sc-004-diana": [
    {
      id: "tr-401",
      event_type: "STEP_START",
      tool_name: "get_order",
      status: "success",
      message: "Reading high-value order ord-004-flagship (NovaBeam 4K Smart Projector - $520.00).",
      created_at: new Date(Date.now() - 200000).toISOString()
    },
    {
      id: "tr-402",
      event_type: "TOOL_CALL",
      tool_name: "evaluate_policy",
      status: "warning",
      message: "Policy evaluation flagged high risk: refund amount $520.00 exceeds $100.00 autonomous threshold.",
      created_at: new Date(Date.now() - 180000).toISOString()
    },
    {
      id: "tr-403",
      event_type: "APPROVAL_GATE",
      tool_name: "request_human_approval",
      status: "warning",
      message: "Autonomous execution suspended. Awaiting supervisor approval before initiating financial mutation.",
      created_at: new Date(Date.now() - 150000).toISOString()
    }
  ]
};

export default async function handler(req, res) {
  const { id } = req.query;

  if (process.env.BACKEND_URL) {
    try {
      const resp = await fetch(`${process.env.BACKEND_URL}/api/agent/case/${id}/trace`);
      if (resp.ok) {
        const data = await resp.json();
        return res.status(200).json(data);
      }
    } catch (_) {}
  }

  const trace = TRACES[id] || [
    {
      id: "tr-default-1",
      event_type: "INVESTIGATION",
      tool_name: "get_order",
      status: "success",
      message: `Auditing active telemetry and policy verification for case ${id}.`,
      created_at: new Date().toISOString()
    }
  ];

  res.setHeader("Cache-Control", "no-cache, no-store, must-revalidate");
  return res.status(200).json(trace);
}

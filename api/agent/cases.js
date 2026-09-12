// Vercel Serverless Function: GET /api/agent/cases

const CASES = [
  {
    id: "sc-002-bob",
    customer_id: "c-002",
    customer_name: "Bob Martinez",
    customer_email: "scenario2_bob@example.com",
    order_id: "ord-002-dallas",
    product_name: "UltraSharp 4K Monitor",
    order_amount: 349.99,
    issue_type: "damaged_in_transit",
    customer_goal: "Screen arrived shattered. Needs immediate replacement before project deadline.",
    status: "replanning",
    risk_level: "medium",
    current_plan: ["get_order", "check_inventory", "search_alternative_inventory", "create_replacement", "verify_resolution"],
    current_step: "search_alternative_inventory",
    resolution_type: "replacement",
    resolution_status: "in_progress",
    requires_approval: false,
    created_at: new Date(Date.now() - 300000).toISOString(),
    updated_at: new Date(Date.now() - 15000).toISOString()
  },
  {
    id: "sc-004-diana",
    customer_id: "c-004",
    customer_name: "Diana Prince",
    customer_email: "scenario4_diana@example.com",
    order_id: "ord-004-flagship",
    product_name: "NovaBeam 4K Smart Projector",
    order_amount: 520.00,
    issue_type: "defective_hardware",
    customer_goal: "Hardware optical engine failure. Customer requested full refund.",
    status: "awaiting_approval",
    risk_level: "high",
    current_plan: ["get_customer", "get_order", "evaluate_policy", "request_human_approval", "create_refund", "verify_resolution"],
    current_step: "request_human_approval",
    resolution_type: "refund",
    resolution_status: "pending_approval",
    requires_approval: true,
    created_at: new Date(Date.now() - 600000).toISOString(),
    updated_at: new Date(Date.now() - 60000).toISOString()
  },
  {
    id: "sc-001-alice",
    customer_id: "c-001",
    customer_name: "Alice Chen",
    customer_email: "scenario1_alice@example.com",
    order_id: "ord-001-headset",
    product_name: "NovaSound Wireless ANC Headphones",
    order_amount: 45.00,
    issue_type: "defective_hardware",
    customer_goal: "Left earbud audio cutting out. Requesting direct replacement.",
    status: "resolved",
    risk_level: "low",
    current_plan: ["get_order", "check_inventory", "create_replacement", "verify_resolution"],
    current_step: "verify_resolution",
    resolution_type: "replacement",
    resolution_status: "verified",
    requires_approval: false,
    created_at: new Date(Date.now() - 1200000).toISOString(),
    updated_at: new Date(Date.now() - 300000).toISOString()
  },
  {
    id: "sc-008-hannah",
    customer_id: "c-008",
    customer_name: "Hannah Abbott",
    customer_email: "scenario8_hannah@example.com",
    order_id: "ord-008-transit",
    product_name: "Ergonomic Mechanical Keyboard",
    order_amount: 89.99,
    issue_type: "cancellation_request",
    customer_goal: "Cancel order placed yesterday; item already dispatched via UPS.",
    status: "escalated",
    risk_level: "medium",
    current_plan: ["get_shipment", "cancel_order", "guide_return_flow"],
    current_step: "cancel_order",
    resolution_type: "cancellation",
    resolution_status: "conflict_blocked",
    requires_approval: false,
    created_at: new Date(Date.now() - 900000).toISOString(),
    updated_at: new Date(Date.now() - 180000).toISOString()
  },
  {
    id: "sc-003-charlie",
    customer_id: "c-003",
    customer_name: "Charlie Brown",
    customer_email: "scenario3_charlie@example.com",
    order_id: "ord-003-dock",
    product_name: "NovaCharge 100W USB-C Dock",
    order_amount: 45.00,
    issue_type: "damaged_packaging",
    customer_goal: "Damaged port on arrival. Refund requested under standard 30-day window.",
    status: "resolved",
    risk_level: "low",
    current_plan: ["get_order", "evaluate_policy", "create_refund", "verify_resolution"],
    current_step: "verify_resolution",
    resolution_type: "refund",
    resolution_status: "verified",
    requires_approval: false,
    created_at: new Date(Date.now() - 1500000).toISOString(),
    updated_at: new Date(Date.now() - 400000).toISOString()
  }
];

export default async function handler(req, res) {
  // If external backend configured, try to proxy first
  if (process.env.BACKEND_URL) {
    try {
      const resp = await fetch(`${process.env.BACKEND_URL}/api/agent/cases`);
      if (resp.ok) {
        const data = await resp.json();
        return res.status(200).json(data);
      }
    } catch (_) {
      // Fallback to local serverless cases
    }
  }

  res.setHeader("Cache-Control", "no-cache, no-store, must-revalidate");
  return res.status(200).json(CASES);
}

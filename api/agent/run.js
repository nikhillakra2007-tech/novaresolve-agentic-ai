// Vercel Serverless Function: POST /api/agent/run

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method Not Allowed' });
  }

  const { case_id } = req.body || {};

  // If external backend configured, forward to FastAPI
  if (process.env.BACKEND_URL) {
    try {
      const resp = await fetch(`${process.env.BACKEND_URL}/api/agent/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ case_id })
      });
      if (resp.ok) {
        const data = await resp.json();
        return res.status(200).json(data);
      }
    } catch (_) {}
  }

  // Deterministic serverless simulation based on scenario
  if (case_id === 'sc-004-diana') {
    return res.status(200).json({
      success: true,
      case_id: case_id,
      status: 'awaiting_approval',
      resolution_status: 'pending_approval',
      requires_approval: true,
      current_step: 'request_human_approval',
      final_outcome: 'Refund amount $520.00 exceeds $100.00 autonomous threshold. Staged for supervisor approval.',
      reason: 'Refund amount exceeds autonomous approval threshold ($100.00).',
      steps_executed: 4,
      replans: 0,
      execution_trace: [
        {
          id: 'tr-401',
          event_type: 'STEP_START',
          tool_name: 'get_order',
          status: 'success',
          message: 'Fetching order details for ord-004-flagship.',
          created_at: new Date().toISOString()
        },
        {
          id: 'tr-402',
          event_type: 'TOOL_CALL',
          tool_name: 'evaluate_policy',
          status: 'warning',
          message: 'Risk policy flagged: $520.00 refund requires human approval.',
          created_at: new Date().toISOString()
        },
        {
          id: 'tr-403',
          event_type: 'APPROVAL_GATE',
          tool_name: 'request_human_approval',
          status: 'warning',
          message: 'Halted before mutation. Awaiting supervisor approval in dashboard.',
          created_at: new Date().toISOString()
        }
      ]
    });
  }

  // Default scenario (e.g. Bob Martinez adaptive replanning)
  return res.status(200).json({
    success: true,
    case_id: case_id || 'sc-002-bob',
    status: 'resolved',
    resolution_status: 'verified',
    requires_approval: false,
    current_step: 'verify_resolution',
    final_outcome: 'Primary warehouse out of stock (Dallas: 0). Autonomously discovered Reno West Warehouse (15 units) and routed replacement. Verified in database.',
    reason: 'Autonomous replacement rerouted through alternate warehouse.',
    steps_executed: 6,
    replans: 1,
    execution_trace: [
      {
        id: 'tr-run-1',
        event_type: 'TOOL_CALL',
        tool_name: 'check_inventory',
        status: 'warning',
        message: 'Primary warehouse stock check: Dallas Central Warehouse has 0 units.',
        created_at: new Date(Date.now() - 4000).toISOString()
      },
      {
        id: 'tr-run-2',
        event_type: 'CONSTRAINT_DETECTED',
        tool_name: 'check_inventory',
        status: 'warning',
        message: 'Inventory constraint detected. Replanner activated.',
        created_at: new Date(Date.now() - 3000).toISOString()
      },
      {
        id: 'tr-run-3',
        event_type: 'TOOL_CALL',
        tool_name: 'search_alternative_inventory',
        status: 'success',
        message: 'Found eligible hub: Reno West Warehouse (15 units in stock).',
        created_at: new Date(Date.now() - 2000).toISOString()
      },
      {
        id: 'tr-run-4',
        event_type: 'TOOL_CALL',
        tool_name: 'create_replacement',
        status: 'success',
        message: 'Created replacement order rep-9941 routing fulfillment to Reno West Warehouse.',
        created_at: new Date(Date.now() - 1000).toISOString()
      },
      {
        id: 'tr-run-5',
        event_type: 'VERIFICATION',
        tool_name: 'verify_resolution',
        status: 'success',
        message: 'Independent verification confirmed inventory reservation and replacement status.',
        created_at: new Date().toISOString()
      }
    ]
  });
}

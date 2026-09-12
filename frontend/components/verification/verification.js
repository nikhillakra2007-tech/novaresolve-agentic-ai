/* Verification Component Logic: Trace, Evidence & Verification Views */

export function getCaseSteps(c, isPlaying, moneyHelper, activePersonaName) {
  if (c.id === 'NR-1024') {
    const entries = [
      ['Customer identified', 'Customer and account information retrieved', 'get_customer', 'Account matched to Rahul Sharma. Customer identity confirmed.', '0.2s'],
      ['Order inspected', `Order #${c.order} · ${c.product}`, 'get_order', 'Delivered 2 days ago. Quantity: 1. Customer reported damage on arrival.', '0.4s'],
      ['Policy evaluated', 'Replacement eligible within the 7-day window', 'evaluate_policy', 'Damaged-on-arrival policy applies. Replacement permitted. Low risk.', '0.3s'],
      ['Inventory checked', 'Delhi warehouse · 0 units available', 'check_inventory', 'Requested SKU: NS-WH-01. Delhi available quantity: 0. Reservation not attempted.', '0.6s'],
      ['Constraint detected', 'Original warehouse cannot fulfill this replacement', 'observe_constraint', 'Inventory = 0. Original replacement route is blocked; the customer goal is retained.', '0.1s'],
      ['Agent replanning', 'Finding another way to fulfill the customer’s goal', 'find_alternative_inventory', 'Searching eligible warehouses for the same SKU. Preserve quantity, policy eligibility, and risk limits.', '1.2s'],
      ['Alternative found', 'Jaipur warehouse · 4 units available', 'check_alternative_inventory', 'Jaipur has 4 units of NS-WH-01. One unit can be reserved. Resolution plan updated.', '0.5s'],
      ['Replacement executed', '1 unit reserved · fulfillment routed to Jaipur', 'create_replacement', 'Replacement RP-2084 created for order NC-48391. Warehouse: Jaipur. Quantity: 1.', '0.8s'],
      ['Verification successful', 'Replacement and inventory reservation confirmed', 'verify_resolution', 'Expected: replacement created, quantity 1 reserved. Observed: RP-2084 created, quantity 1 reserved. Match confirmed.', '0.3s']
    ];
    return entries.map(([title, detail, tool, evidence, duration], i) => ({
      title,
      detail,
      tool,
      evidence,
      duration,
      state: i > c.stage ? 'waiting' : i === c.stage && c.stage < 9 ? (i === 4 ? 'warning' : 'active') : i === 4 ? 'warning' : i === 8 ? 'verified' : 'completed'
    }));
  }

  if (c.decision === 'reject') {
    return [
      { title: 'Customer and order identified', detail: `${c.customer} · Order #${c.order}`, tool: 'get_order', evidence: c.product, state: 'completed', duration: '0.4s' },
      { title: 'Policy and risk evaluated', detail: 'Refund exceeds the autonomous approval threshold', tool: 'evaluate_policy', evidence: c.reason, state: 'completed', duration: '0.3s' },
      { title: 'Human approval requested', detail: `Proposed refund: ${moneyHelper(c.amount)}`, tool: 'request_approval', evidence: c.recommendation, state: 'completed', duration: 'Reviewed' },
      { title: 'Approval rejected', detail: 'A resolution specialist must review this case', tool: 'approval_decision', evidence: c.decisionNote || 'Rejected by the resolution manager.', state: 'failed', duration: 'Just now' }
    ];
  }

  const plan = [
    { title: 'Customer identified', detail: `${c.customer} · Account matched`, tool: 'get_customer', evidence: `Customer account located for ${c.email}.`, duration: '0.2s' },
    { title: 'Order inspected', detail: `Order #${c.order} · ${c.product}`, tool: 'get_order', evidence: `Order value: ${moneyHelper(c.amount)}. Requested resolution: ${c.resolution}.`, duration: '0.4s' },
    { title: 'Policy and risk evaluated', detail: `${c.risk} risk · ${c.resolution} eligibility reviewed`, tool: 'evaluate_policy', evidence: c.status === 'Escalated' ? c.reason : `Resolution request checked against the applicable ${c.resolution.toLowerCase()} policy. ${c.risk} risk.`, duration: '0.3s' },
    { title: c.decision === 'approve' ? 'Human approval recorded' : c.status === 'Awaiting Approval' ? 'Human approval required' : 'Resolution planned', detail: c.decision === 'approve' ? `Approved by ${activePersonaName}${c.decisionNote ? ' · ' + c.decisionNote : ''}` : c.status === 'Awaiting Approval' ? c.reason : c.recommendation, tool: c.decision || c.status === 'Awaiting Approval' ? 'approval_decision' : 'plan_resolution', evidence: c.recommendation, duration: c.decision === 'approve' ? 'Approved' : '0.3s' },
    { title: `${c.resolution} executed`, detail: c.resolution === 'Refund' ? `Refund of ${moneyHelper(c.amount)} submitted` : c.resolution === 'Replacement' ? 'Replacement created · 1 unit reserved' : 'Cancellation submitted', tool: 'execute_resolution', evidence: `${c.resolution} action recorded for order ${c.order}. Verification is required before resolution.`, duration: '0.6s' },
    { title: 'Resolution verification', detail: c.verified ? c.reason : 'Compare the observed result with the expected outcome', tool: 'verify_resolution', evidence: c.verified ? 'Expected and observed states match. The outcome is verified.' : c.reason, duration: '0.3s' }
  ];

  let step = { Investigating: 1, Planning: 3, 'Awaiting Approval': 3, Executing: 4, Verifying: 5, Resolved: 6, Escalated: 2, Failed: 5 }[c.status] ?? 0;
  return plan.map((s, i) => ({
    ...s,
    state: i > step ? 'waiting' : i === step ? (c.status === 'Escalated' || c.status === 'Failed' ? 'failed' : c.status === 'Awaiting Approval' ? 'warning' : 'active') : c.verified && i === 5 ? 'verified' : 'completed'
  }));
}

export function renderTraceHtml(c, steps, expandedSet, isPlaying, iconHelper, esc) {
  const completedCount = steps.filter(s => ['completed', 'verified'].includes(s.state) || (s.state === 'warning' && c.id === 'NR-1024' && c.stage > 4)).length;
  
  return `
    <div class="trace-content">
      <div class="trace-intro">
        <div>
          <strong>Step-by-step execution</strong>
          <span class="step-count">${completedCount} of ${steps.length} steps complete</span>
        </div>
        <button class="text-button" data-action="expand-all">${expandedSet.size ? 'Collapse' : 'Expand'} details</button>
      </div>
      <ol class="timeline">
        ${steps.map((s, i) => {
          const active = s.state === 'active';
          const waiting = s.state === 'waiting';
          const open = expandedSet.has(`${c.id}-${i}`);
          const symbol = s.state === 'warning' ? 'warning' : s.state === 'failed' ? 'x' : waiting ? 'clock' : active ? (c.id === 'NR-1024' && i === 5 ? 'refresh' : 'activity') : s.state === 'verified' ? 'circleCheck' : 'check';
          return `
            <li class="step ${s.state}">
              <span class="step-icon">${iconHelper(symbol, isPlaying && active ? 'spinning' : '')}</span>
              <button class="step-head" data-action="step" data-step="${i}" aria-expanded="${open}" aria-controls="step-detail-${i}" ${waiting ? 'disabled' : ''}>
                <span class="step-name">${esc(s.title)}</span>
                ${active ? '<span class="badge blue">In progress</span>' : ''}
                <span class="step-time">${waiting ? 'Queued' : active ? 'Now' : s.duration}</span>
                ${!waiting ? iconHelper('down', 'step-chevron') : ''}
              </button>
              ${!waiting && !active ? `<p class="step-brief">${esc(s.detail)}</p>` : ''}
              ${open || active ? `
                <div class="step-body" id="step-detail-${i}">
                  <span class="tool-code">${esc(s.tool)}()</span>
                  <p style="margin: 4px 0 0;">${esc(s.evidence)}</p>
                </div>
              ` : ''}
            </li>
          `;
        }).join('')}
      </ol>
    </div>
  `;
}

export function renderEvidenceHtml(c, iconHelper, esc) {
  return `
    <div class="evidence-content">
      <div class="evidence-card">
        <h4>${iconHelper('file')} Customer Statement & Evidence</h4>
        <p>${esc(c.reason)}</p>
      </div>
      <div class="evidence-card">
        <h4>${iconHelper('shield')} Policy Evaluation</h4>
        <p>${esc(c.recommendation)}</p>
      </div>
      <div class="evidence-card">
        <h4>${iconHelper('database')} System Forensics & Order Snapshot</h4>
        <p>Order #${c.order} · Customer: ${esc(c.customer)} (${esc(c.email)}) · Item: ${esc(c.product)} · Risk evaluation: ${esc(c.risk)}</p>
      </div>
    </div>
  `;
}

export function renderVerificationHtml(c, iconHelper, esc) {
  return `
    <div class="verification-card">
      <div class="verification-status-banner ${c.verified ? 'verified' : ''}">
        ${iconHelper(c.verified ? 'circleCheck' : 'shield')}
        <div>
          <strong>${c.verified ? 'Independent State Verification Confirmed' : 'Verification Pending Execution'}</strong>
          <p>${c.verified ? 'Expected and observed database records match precisely. Zero discrepancy detected.' : 'Case must satisfy policy conditions and post-execution inventory balance before marking resolved.'}</p>
        </div>
      </div>
      <div style="font-size: 13px; color: var(--muted); line-height: 1.6;">
        <p><strong>Verification Rule ID:</strong> <code>VR-POLICY-${c.resolution ? c.resolution.toUpperCase() : 'STANDARD'}</code></p>
        <p><strong>Assigned Evaluator:</strong> Automated Verification Engine v2.4 (Independent Assertion Layer)</p>
      </div>
    </div>
  `;
}

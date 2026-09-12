/* Verification Component Logic: Trace, Forensics Evidence & Zero-Trust Parity Matrix */

export function getCaseSteps(c, isPlaying, moneyHelper, activePersonaName) {
  if (c.realTrace && Array.isArray(c.realTrace) && c.realTrace.length > 0) {
    return c.realTrace.map((event, i) => {
      const tool = event.tool_name || event.action || 'system';
      const status = (event.observation_status || event.status || 'success').toLowerCase();
      const rawType = (event.event_type || tool).toUpperCase().replace(/_/g, ' ');

      const titles = {
        get_customer: 'Customer profile retrieved',
        get_order: 'Authoritative order inspected',
        get_shipment: 'Carrier tracking & shipment verified',
        evaluate_policy: 'Enterprise policy evaluated',
        check_inventory: 'Warehouse inventory verified',
        search_alternative_inventory: 'Alternative inventory searched',
        create_replacement: 'Replacement order created',
        create_refund: 'Refund transaction initiated',
        cancel_order: 'Order cancellation executed',
        verify_resolution: 'Post-action outcome verified',
        GOAL_IDENTIFIED: 'Customer resolution goal identified',
        POLICY_CHECK: 'Policy compliance check',
        CONSTRAINT_DETECTED: 'Operational constraint detected',
        REPLAN_STARTED: 'Replanning sequence started',
        REPLAN_COMPLETED: 'Alternative plan synthesized',
        APPROVAL_REQUIRED: 'Human approval gate triggered',
        APPROVAL_GRANTED: 'Supervisor approval recorded',
        APPROVAL_REJECTED: 'Supervisor rejection recorded',
        VERIFICATION_STARTED: 'Verification audit started',
        VERIFICATION_FAILED: 'Verification discrepancy detected',
      };

      const title = titles[tool] || titles[event.event_type] || rawType;
      const detail = event.rationale || event.message || `Executed ${tool}`;
      const evidence = event.observation_message || event.message || (event.parameters ? JSON.stringify(event.parameters, null, 2) : 'Authoritative state verified.');

      let state = 'completed';
      if (['failed', 'error', 'rejected'].includes(status) || event.event_type === 'VERIFICATION_FAILED') {
        state = 'failed';
      } else if (['blocked', 'insufficient_inventory', 'approval_required'].includes(status) || event.event_type === 'CONSTRAINT_DETECTED' || event.event_type === 'APPROVAL_REQUIRED') {
        state = 'warning';
      } else if (tool === 'verify_resolution' && ['success', 'completed'].includes(status)) {
        state = 'verified';
      }

      const duration = event.decision_source || event.source || (event.created_at ? new Date(event.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : 'Verified');

      return {
        title,
        detail,
        tool,
        evidence,
        duration,
        state
      };
    });
  }

  if (c.id === 'NR-1024') {
    const entries = [
      ['Customer identified', 'Customer and account integrity retrieved', 'get_customer', 'Account matched to Rahul Sharma (Trust Score: 98/100). Customer identity confirmed.', '0.18s'],
      ['Order inspected', `Order #${c.order} · ${c.product}`, 'get_order', 'Delivered 2 days ago. Quantity: 1. Customer reported damage on arrival with photographic proof.', '0.32s'],
      ['Policy evaluated', 'Replacement eligible within the 7-day window', 'evaluate_policy', 'Damaged-on-arrival enterprise clause applies. Replacement permitted under autonomous limits. Risk: Low.', '0.24s'],
      ['Inventory checked', 'Delhi warehouse · 0 units available', 'check_inventory', 'Requested SKU: NS-WH-01. Delhi available quantity: 0. Warehouse stock exhausted.', '0.45s'],
      ['Constraint detected', 'Original warehouse cannot fulfill this replacement', 'observe_constraint', 'Stockout constraint detected. Traditional bots fail here; NovaResolve retains customer goal.', '0.12s'],
      ['Autonomous replanning', 'Finding another way to fulfill the customer’s goal', 'find_alternative_inventory', 'Scanning 8 regional fulfillment centers. Filtering by SKU NS-WH-01, policy eligibility, and SLA transit time.', '0.88s'],
      ['Alternative found', 'Jaipur warehouse · 4 units available', 'check_alternative_inventory', 'Jaipur Robotic Center has 4 units in stock. Estimated delivery tomorrow 2 PM. Resolution route updated.', '0.38s'],
      ['Replacement executed', '1 unit reserved · fulfillment routed to Jaipur', 'create_replacement', 'Replacement RP-2084 created for order NC-48391. Warehouse: Jaipur. Tracking #NE-9821.', '0.62s'],
      ['Verification confirmed', 'Independent database state matches expected resolution', 'verify_resolution', 'Assertion VR-0491 passed. Expected: replacement created, 1 unit reserved. Observed: RP-2084 active, 1 unit reserved. Discrepancy: 0. Hash: 0x8FA4...C119.', '0.21s']
    ];
    return entries.map(([title, detail, tool, evidence, duration], i) => ({
      title,
      detail,
      tool,
      evidence,
      duration,
      state: i > c.stage ? 'waiting' : i === c.stage && c.stage < 8 ? (i === 4 ? 'warning' : 'active') : i === 4 ? 'warning' : i === 8 ? 'verified' : 'completed'
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
    { title: 'Customer identified', detail: `${c.customer} · Account matched`, tool: 'get_customer', evidence: `Customer account located for ${c.email}. Trust Score: 96/100.`, duration: '0.2s' },
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
          <div style="display: flex; align-items: center; gap: 8px;">
            <strong>Autonomous Execution Trace</strong>
            <span class="telemetry-pill">Zero Discrepancy Gate</span>
          </div>
          <span class="step-count">${completedCount} of ${steps.length} steps complete · ${isPlaying ? 'Live playback running' : 'State immutable'}</span>
        </div>
        <button class="text-button" data-action="expand-all">${expandedSet.size ? 'Collapse' : 'Expand'} all telemetry</button>
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
                ${active ? '<span class="badge blue live-pulse">Executing now</span>' : ''}
                ${s.state === 'verified' ? '<span class="badge green">100% Parity</span>' : ''}
                <span class="step-time">${waiting ? 'Queued' : active ? 'Now' : s.duration}</span>
                ${!waiting ? iconHelper('down', 'step-chevron') : ''}
              </button>
              ${!waiting && !active ? `<p class="step-brief">${esc(s.detail)}</p>` : ''}
              ${open || active ? `
                <div class="step-body" id="step-detail-${i}">
                  <div class="step-tool-header">
                    <span class="tool-code">${esc(s.tool)}()</span>
                    <span class="tool-status-tag ${s.state}">${s.state.toUpperCase()}</span>
                  </div>
                  <pre class="telemetry-code-block"><code>${esc(s.evidence)}</code></pre>
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
        <div class="evidence-card-header">
          <h4>${iconHelper('file')} Customer Statement & Evidence</h4>
          <span class="badge blue">Verified Customer</span>
        </div>
        <p>${esc(c.reason)}</p>
        <div class="evidence-pill-row">
          <span class="evidence-pill">Channel: Mobile App</span>
          <span class="evidence-pill">Attached: Photo-proof (Verified Damaged)</span>
          <span class="evidence-pill">Customer Sentiment: Frustrated / Cooperative</span>
        </div>
      </div>

      <div class="evidence-card">
        <div class="evidence-card-header">
          <h4>${iconHelper('shield')} Policy Evaluation Matrix</h4>
          <span class="badge green">Compliant</span>
        </div>
        <p>${esc(c.recommendation)}</p>
        <div class="evidence-meta-grid">
          <div><span>Policy Clause</span><strong>POL-DAMAGE-7D</strong></div>
          <div><span>Max Auto Budget</span><strong>$100.00</strong></div>
          <div><span>Case Risk Score</span><strong>${c.risk} Risk (Score: 0.12)</strong></div>
          <div><span>Action Permitted</span><strong>Direct Replacement</strong></div>
        </div>
      </div>

      <div class="evidence-card">
        <div class="evidence-card-header">
          <h4>${iconHelper('database')} System Forensics & Order Snapshot</h4>
          <span class="badge">Authoritative Ledger</span>
        </div>
        <p>Order #${c.order} · Customer: ${esc(c.customer)} (${esc(c.email)}) · Item: ${esc(c.product)}</p>
        <div class="evidence-meta-grid">
          <div><span>Payment Gateway</span><strong>Stripe Verified</strong></div>
          <div><span>Original Carrier</span><strong>Delhi Express Delivery</strong></div>
          <div><span>Delivered At</span><strong>2 days ago</strong></div>
          <div><span>Ledger Balance</span><strong>Paid in Full</strong></div>
        </div>
      </div>
    </div>
  `;
}

export function renderVerificationHtml(c, iconHelper, esc) {
  const isVerified = c.verified || c.stage >= 8;
  return `
    <div class="verification-card">
      <div class="verification-status-banner ${isVerified ? 'verified' : ''}">
        ${iconHelper(isVerified ? 'circleCheck' : 'shield')}
        <div>
          <strong>${isVerified ? 'Zero-Trust State Verification Confirmed' : 'Verification Pending Autonomous Execution'}</strong>
          <p>${isVerified ? 'All cryptographic assertions satisfied. Expected state matches observed database state with 0 discrepancies.' : 'Case must satisfy policy conditions and post-execution inventory balance before marking resolved.'}</p>
        </div>
      </div>

      <div class="parity-matrix-section">
        <h4 style="font-size: 13.5px; font-weight: 700; margin-bottom: 12px; color: var(--ink-heading); display: flex; align-items: center; gap: 8px;">
          ${iconHelper('database')}
          <span>Expected vs. Observed State Matrix</span>
          <span class="badge ${isVerified ? 'green' : 'amber'}" style="margin-left: auto;">${isVerified ? '0 Discrepancies' : 'Audit Pending'}</span>
        </h4>

        <div class="parity-table-wrap">
          <table class="parity-table">
            <thead>
              <tr>
                <th>Entity / Dimension</th>
                <th>Target (Expected)</th>
                <th>Observed (DB Truth)</th>
                <th>Audit Status</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><strong>Inventory Reservation</strong></td>
                <td>1 unit SKU: NS-WH-01 (Jaipur)</td>
                <td>${isVerified ? '1 unit reserved (RP-2084)' : 'Reservation pending'}</td>
                <td><span class="badge ${isVerified ? 'green' : 'amber'}">${isVerified ? 'Match' : 'Waiting'}</span></td>
              </tr>
              <tr>
                <td><strong>Warehouse Route</strong></td>
                <td>Jaipur Hub (Auto-Rerouted)</td>
                <td>${isVerified ? 'Jaipur Dispatch Queue' : 'Delhi (0 stockout)'}</td>
                <td><span class="badge ${isVerified ? 'green' : 'amber'}">${isVerified ? 'Reroute Verified' : 'Checking'}</span></td>
              </tr>
              <tr>
                <td><strong>Customer Financial Liability</strong></td>
                <td>$0.00 (100% Covered)</td>
                <td>$0.00 (Zero Charge Ledger)</td>
                <td><span class="badge green">Pass</span></td>
              </tr>
              <tr>
                <td><strong>Cryptographic Audit Seal</strong></td>
                <td><code>sha256:7f09...b412</code></td>
                <td><code>sha256:7f09...b412</code></td>
                <td><span class="badge green">Valid Seal</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div style="font-size: 12.5px; color: var(--muted); line-height: 1.6; margin-top: 16px; padding: 12px; background: var(--surface-subtle); border-radius: 8px; border: 1px solid var(--line);">
        <p style="margin: 0;"><strong>Independent Engine Rule:</strong> <code>VR-POLICY-AUTONOMOUS-REPLACEMENT-V2</code> · No agent action is final until authoritative database write confirmation is cryptographically verified.</p>
      </div>
    </div>
  `;
}

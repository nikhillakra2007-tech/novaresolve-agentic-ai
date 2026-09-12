/* Approvals Component Logic: Human Oversight & Decision Cards */

export function renderApprovalPanel(pendingCase, pendingCount, moneyHelper, avatarHelper, iconHelper, esc) {
  if (!pendingCase) {
    return `
      <section class="panel approval-panel" aria-label="Human oversight">
        <div class="panel-header">
          <span class="badge green">${iconHelper('circleCheck')}Queue clear</span>
        </div>
        <div class="approval-content" style="text-align: center; color: var(--muted); padding: 28px 16px;">
          <p style="margin: 0;">No decisions currently awaiting human approval.</p>
        </div>
      </section>
    `;
  }

  return `
    <section class="panel approval-panel" aria-label="Human approval required for ${pendingCase.id}">
      <div class="panel-header">
        <div>
          <span class="badge amber">${iconHelper('shield')}Human approval required</span>
          <span class="badge" style="margin-left: 6px;">${pendingCount} pending</span>
        </div>
      </div>
      <div class="approval-content">
        <div class="person">
          ${avatarHelper(pendingCase.customer, pendingCase.tone)}
          <div>
            <strong>${esc(pendingCase.customer)}</strong>
            <small>${pendingCase.id} · ${esc(pendingCase.goal)}</small>
          </div>
        </div>
        <div class="approval-figure">
          <div>
            <span>Proposed ${pendingCase.resolution.toLowerCase()}</span>
            <strong>${moneyHelper(pendingCase.amount)}</strong>
          </div>
          <span class="badge red">${iconHelper('warning')}${esc(pendingCase.risk)} risk</span>
        </div>
        <p class="approval-reason">${esc(pendingCase.reason)}</p>
        <div class="approval-actions">
          <button class="button reject" data-action="review" data-id="${pendingCase.id}" data-decision="reject">${iconHelper('x')}Reject</button>
          <button class="button approve" data-action="review" data-id="${pendingCase.id}" data-decision="approve">${iconHelper('check')}Approve</button>
        </div>
      </div>
    </section>
  `;
}

export function renderContextPanel(iconHelper) {
  return `
    <section class="panel context-panel" aria-label="Autonomous policy guarantees">
      <div class="context-title">
        ${iconHelper('shield')}
        <span>Operational Safeguards Active</span>
      </div>
      <p class="context-copy">
        All agent actions are checked against policies and risk parameters. A case is resolved only after independent state verification confirms database parity.
      </p>
    </section>
  `;
}

export function renderCustomerSidePanel(iconHelper) {
  return `
    <section class="panel customer-side-card" aria-label="Customer Order Protection">
      <div class="panel-header">
        <div>
          <span class="badge green">${iconHelper('circleCheck')}Autonomous Guarantee</span>
          <h2 style="font-size: 15px; margin-top: 6px;">Protected Order #NC-48391</h2>
        </div>
      </div>
      <div class="customer-side-body">
        <div class="customer-side-item">
          ${iconHelper('package')}
          <div>
            <strong style="display: block; font-family: var(--font-display); color: var(--ink-heading);">NovaSound Wireless Headphones</strong>
            <small style="color: var(--muted); font-family: var(--font-mono);">₹3,499 · Delivered Sept 10</small>
          </div>
        </div>
        <p style="margin: 0 0 10px; color: var(--muted);">
          Your replacement request was approved automatically by NovaCart Policy. Because our Delhi warehouse was out of stock, our agent dynamically routed your shipment from Jaipur with zero delay.
        </p>
        <div class="customer-side-grid">
          <div>
            <span>Dispatch Hub</span>
            <strong>Jaipur Fulfillment</strong>
          </div>
          <div>
            <span>Estimated Arrival</span>
            <strong style="color: var(--green);">Tomorrow, 2 PM</strong>
          </div>
        </div>
      </div>
    </section>
    <section class="panel" style="padding: 16px;" aria-label="Transparency">
      <div style="display: flex; align-items: center; gap: 10px; color: var(--muted); font-size: 12.5px;">
        ${iconHelper('shield')}
        <span><strong>100% Policy Transparency</strong> · Every agent calculation is verified against NovaCart standards.</span>
      </div>
    </section>
  `;
}

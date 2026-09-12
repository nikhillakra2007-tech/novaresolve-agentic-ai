/* Metrics Component Logic */

export function renderHeadingHtml(title, subtitle, persona, actionsHtml, view, esc) {
  return `
    <div class="page-heading">
      <div>
        ${view === 'overview' ? `<div class="greeting">${esc(persona.greeting)}</div>` : ''}
        <h1>
          <span>${title}</span>
          ${view === 'overview' ? `<span class="persona-role-pill ${persona.key}"><span class="dot"></span>${esc(persona.badgeText)}</span>` : ''}
        </h1>
        <p>${subtitle}</p>
      </div>
      ${actionsHtml ? `<div class="heading-actions">${actionsHtml}</div>` : ''}
    </div>
  `;
}

export function renderMetricsCards(activePersonaKey, cases, pendingCases, terminalStatuses, iconHelper) {
  if (activePersonaKey === 'specialist') {
    const escalatedCount = cases.filter(c => c.status === 'Escalated').length;
    const highRiskCount = cases.filter(c => c.risk === 'High' && c.status === 'Awaiting Approval').length;
    const investigatingCount = cases.filter(c => ['Investigating', 'Replanning'].includes(c.status)).length;
    const today = new Date().toDateString();
    const resolvedCount = cases.filter(c => c.status === 'Resolved' && new Date(c.updated).toDateString() === today).length;
    const data = [
      ['Assigned Escalations', escalatedCount, 'external', 'High-priority dispute', 'Escalated', 'primary'],
      ['High-Risk Approvals', highRiskCount, 'shield', 'Exceeds ₹10k threshold', 'Awaiting Approval', 'amber-text'],
      ['Evidence Forensics', investigatingCount, 'search', 'Under investigation', 'active', ''],
      ['Policy Overrides', 1, 'sliders', 'Discretionary queue', 'all', ''],
      ['Resolved Disputes', resolvedCount, 'circleCheck', 'Verified outcomes', 'Resolved', 'green-text']
    ];
    return renderGrid(data, iconHelper);
  }

  if (activePersonaKey === 'customer') {
    const data = [
      ['Active Order', '1', 'package', 'Order #NC-48391', 'all', 'primary'],
      ['Resolution Type', 'Replacement', 'refresh', '7-day policy approved', 'all', ''],
      ['Fulfillment Route', 'Jaipur Hub', 'route', 'Rerouted from Delhi', 'all', 'amber-text'],
      ['Estimated Arrival', 'Tomorrow 2 PM', 'clock', 'Express delivery', 'all', 'green-text'],
      ['Customer Fee', '₹0.00', 'circleCheck', '100% covered by NovaCart', 'all', 'green-text']
    ];
    return renderGrid(data, iconHelper);
  }

  // Default: Manager (Alex Morgan)
  const active = cases.filter(c => !terminalStatuses.includes(c.status)).length;
  const running = cases.filter(c => ['Investigating', 'Planning', 'Executing', 'Replanning', 'Verifying'].includes(c.status)).length;
  const today = new Date().toDateString();
  const data = [
    ['Active cases', active, 'cases', 'In your workspace', 'active', 'primary'],
    ['Agent resolving', running, 'bolt', 'Working on a solution', 'resolving', ''],
    ['Awaiting approval', pendingCases.length, 'shield', 'Ready for your review', 'Awaiting Approval', 'amber-text'],
    ['Escalated', cases.filter(c => c.status === 'Escalated').length, 'external', 'Specialist attention', 'Escalated', 'red-text'],
    ['Resolved today', cases.filter(c => c.status === 'Resolved' && new Date(c.updated).toDateString() === today).length, 'circleCheck', 'Verified outcomes', 'Resolved', 'green-text']
  ];
  return renderGrid(data, iconHelper);
}

function renderGrid(data, iconHelper) {
  return `
    <section class="metrics" aria-label="Resolution status metrics">
      ${data.map(([label, value, symbol, detail, filter, cls]) => `
        <button class="metric ${cls === 'primary' ? 'primary' : ''}" data-action="metric" data-filter="${filter}" aria-label="${label}: ${value}. View cases">
          <span class="metric-label">
            <span>${label}</span>
            <span class="metric-icon">${iconHelper(symbol)}</span>
          </span>
          <strong class="number">${String(value)}</strong>
          <p class="${cls}">${cls === 'green-text' ? iconHelper('check') : ''}${detail}</p>
        </button>
      `).join('')}
    </section>
  `;
}

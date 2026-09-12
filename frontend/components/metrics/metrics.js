/* Metrics Component Logic with Live Sparklines & Real-time Telemetry */

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

function generateSparkline(trend = 'up', color = '#3b82f6') {
  const points = trend === 'up' 
    ? '0,22 10,18 20,20 30,14 40,16 50,8 60,10 70,4'
    : trend === 'amber'
    ? '0,8 10,12 20,10 30,16 40,14 50,18 60,12 70,16'
    : '0,20 10,16 20,18 30,12 40,14 50,6 60,8 70,2';

  return `
    <svg class="sparkline" viewBox="0 0 70 24" preserveAspectRatio="none" aria-hidden="true">
      <polyline points="${points}" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
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
      ['Assigned Escalations', escalatedCount, 'external', 'High-priority dispute', 'Escalated', 'primary', '#3b82f6', 'up'],
      ['High-Risk Approvals', highRiskCount, 'shield', 'Exceeds ₹10k threshold', 'Awaiting Approval', 'amber-text', '#f59e0b', 'amber'],
      ['Evidence Forensics', investigatingCount, 'search', 'Under investigation', 'active', '', '#6366f1', 'up'],
      ['Policy Overrides', 1, 'sliders', 'Discretionary queue', 'all', '', '#8b5cf6', 'up'],
      ['Resolved Disputes', resolvedCount, 'circleCheck', 'Verified outcomes', 'Resolved', 'green-text', '#10b981', 'up']
    ];
    return renderGrid(data, iconHelper);
  }

  if (activePersonaKey === 'customer') {
    const data = [
      ['Active Order', '1', 'package', 'Order #NC-48391', 'all', 'primary', '#3b82f6', 'up'],
      ['Resolution Type', 'Replacement', 'refresh', '7-day policy approved', 'all', '', '#6366f1', 'up'],
      ['Fulfillment Route', 'Jaipur Hub', 'route', 'Rerouted from Delhi', 'all', 'amber-text', '#f59e0b', 'amber'],
      ['Estimated Arrival', 'Tomorrow 2 PM', 'clock', 'Express delivery', 'all', 'green-text', '#10b981', 'up'],
      ['Customer Fee', '₹0.00', 'circleCheck', '100% covered by NovaCart', 'all', 'green-text', '#10b981', 'up']
    ];
    return renderGrid(data, iconHelper);
  }

  // Default: Manager (Alex Morgan)
  const active = cases.filter(c => !terminalStatuses.includes(c.status)).length;
  const running = cases.filter(c => ['Investigating', 'Planning', 'Executing', 'Replanning', 'Verifying'].includes(c.status)).length;
  const today = new Date().toDateString();
  const data = [
    ['Active Cases', active, 'cases', 'Live pipeline', 'active', 'primary', '#3b82f6', 'up'],
    ['Autonomous Resolving', running, 'bolt', 'Agent active', 'resolving', '', '#06b6d4', 'up'],
    ['Awaiting Approval', pendingCases.length, 'shield', 'Requires review', 'Awaiting Approval', 'amber-text', '#f59e0b', 'amber'],
    ['Escalations', cases.filter(c => c.status === 'Escalated').length, 'external', 'Specialist attention', 'Escalated', 'red-text', '#f43f5e', 'amber'],
    ['Resolved Today', cases.filter(c => c.status === 'Resolved' && new Date(c.updated).toDateString() === today).length, 'circleCheck', '98.8% verified', 'Resolved', 'green-text', '#10b981', 'up']
  ];
  return renderGrid(data, iconHelper);
}

function renderGrid(data, iconHelper) {
  return `
    <section class="metrics" aria-label="Resolution status metrics">
      ${data.map(([label, value, symbol, detail, filter, cls, sparkColor, trend]) => `
        <button class="metric ${cls === 'primary' ? 'primary' : ''}" data-action="metric" data-filter="${filter}" aria-label="${label}: ${value}. View cases">
          <div class="metric-top">
            <span class="metric-label">
              <span>${label}</span>
            </span>
            <span class="metric-icon" style="color: ${sparkColor};">${iconHelper(symbol)}</span>
          </div>
          <div class="metric-main">
            <strong class="number">${String(value)}</strong>
            <div class="sparkline-wrapper">
              ${generateSparkline(trend, sparkColor)}
            </div>
          </div>
          <p class="${cls}">
            ${cls === 'green-text' ? iconHelper('check') : ''}
            <span>${detail}</span>
          </p>
        </button>
      `).join('')}
    </section>
  `;
}

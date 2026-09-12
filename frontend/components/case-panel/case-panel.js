/* Case Panel Component Logic */

export function renderCasePanelHtml(c, activeTab, isPlaying, focusMode, badgeHelper, avatarHelper, iconHelper, esc, tabsContentHtml) {
  const moving = (isPlaying && c.id === 'NR-1024') || (c.decision === 'approve' && ['Executing', 'Verifying'].includes(c.status));
  const activeLabel = moving ? 'Agent working now' : c.verified ? 'Verified outcome' : ['Resolved', 'Escalated', 'Failed'].includes(c.status) ? 'Review the outcome' : 'CURRENT AGENT STATE';
  const color = c.verified ? 'green' : c.status === 'Awaiting Approval' ? 'amber' : ['Escalated', 'Failed'].includes(c.status) ? 'red' : 'blue';

  const titles = {
    Investigating: 'Getting the full picture.',
    Planning: 'Choosing the right next step.',
    'Awaiting Approval': 'A decision only you can make.',
    Executing: 'Putting the plan into action.',
    Replanning: 'A new route. The same promise.',
    Verifying: 'Making sure it actually worked.',
    Resolved: 'Resolved. And double-checked.',
    Escalated: 'Over to a resolution specialist.',
    Failed: 'This outcome needs a closer look.'
  };

  let routeHtml = '';
  if (c.id === 'NR-1024' && c.stage >= 4) {
    const found = c.stage >= 6;
    routeHtml = `
      <div class="route-map" aria-label="Fulfillment route">
        <div class="route-node blocked">
          ${iconHelper('package')}
          <div>
            <strong>Delhi</strong>
            <small>No inventory</small>
          </div>
        </div>
        <span class="route-connector ${moving ? 'moving' : ''}" aria-hidden="true"></span>
        <div class="route-node ${found ? 'found' : ''}">
          ${iconHelper(found ? 'circleCheck' : 'search')}
          <div>
            <strong>${found ? 'Jaipur' : 'Alternative route'}</strong>
            <small>${c.stage >= 7 ? '1 unit reserved' : found ? '4 units available' : 'Searching inventory'}</small>
          </div>
        </div>
      </div>
    `;
  }

  return `
    <section class="panel ${focusMode ? 'spotlight-focus-target' : ''}" id="case-panel" aria-label="Case ${c.id}">
      <div class="panel-header">
        <div>
          <div class="case-topline">
            <span class="case-id">CASE ${c.id}</span>
            ${badgeHelper(c.status)}
          </div>
          <h2 class="case-title">${esc(c.goal)}</h2>
        </div>
        <button class="icon-button" data-action="case-info" aria-label="View case information">${iconHelper('dots')}</button>
      </div>

      <div class="case-goal">
        ${avatarHelper(c.customer, c.tone)}
        <div>
          <strong>${esc(c.customer)}</strong>
          <p>${esc(c.product)}</p>
        </div>
        <div class="goal-meta">
          <span>Order reference</span>
          <strong>#${c.order}</strong>
        </div>
      </div>

      <section class="agent-focus ${color}" aria-label="Current agent decision">
        <div class="focus-label">
          <span class="dot"></span>
          <span>${activeLabel}</span>
          ${moving ? '<span class="focus-animation"><i></i><i></i><i></i></span>' : ''}
        </div>
        <h3 class="focus-title">${titles[c.status] || 'Autonomous resolution'}</h3>
        <p class="focus-copy">${esc(c.reason)}</p>
        ${routeHtml}
      </section>

      <div class="panel-tabs" role="tablist" aria-label="Case information tabs">
        ${[
          ['trace', 'activity', 'Execution trace'],
          ['evidence', 'file', 'Evidence'],
          ['verification', 'shield', 'Verification']
        ].map(([tab, symbol, label]) => `
          <button id="tab-${tab}" role="tab" aria-selected="${activeTab === tab}" aria-controls="case-tab-panel" tabindex="${activeTab === tab ? '0' : '-1'}" class="${activeTab === tab ? 'active' : ''}" data-action="tab" data-tab="${tab}">
            ${iconHelper(symbol)}
            <span>${label}</span>
          </button>
        `).join('')}
      </div>

      <div id="case-tab-panel" role="tabpanel" aria-labelledby="tab-${activeTab}" tabindex="0">
        ${tabsContentHtml}
      </div>
    </section>
  `;
}

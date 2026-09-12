/* Case Queue Component Logic: Filtering, Status Badges & Table View */

export function renderCaseQueueHtml(cases, selectedCaseId, filters, badgeHelper, avatarHelper, iconHelper, agoHelper, esc) {
  let list = [...cases];

  if (filters.filter && filters.filter !== 'all') {
    if (filters.filter === 'active') list = list.filter(c => !['Resolved', 'Escalated', 'Failed'].includes(c.status));
    else if (filters.filter === 'resolving') list = list.filter(c => ['Investigating', 'Planning', 'Executing', 'Replanning', 'Verifying'].includes(c.status));
    else list = list.filter(c => c.status === filters.filter);
  }

  if (filters.risk && filters.risk !== 'all') {
    list = list.filter(c => c.risk.toLowerCase() === filters.risk.toLowerCase());
  }

  if (filters.query) {
    const q = filters.query.toLowerCase();
    list = list.filter(c => c.id.toLowerCase().includes(q) || c.customer.toLowerCase().includes(q) || c.issue.toLowerCase().includes(q) || c.product.toLowerCase().includes(q));
  }

  const shown = list.slice(0, filters.limit || 6);

  return `
    <div class="queue-header">
      <div>
        <h2>Active Case Queue</h2>
        <p>${list.length} cases matching current filters</p>
      </div>
      <div class="queue-tools">
        <select id="status-filter" aria-label="Filter cases by status">
          <option value="all" ${filters.filter === 'all' ? 'selected' : ''}>All statuses</option>
          <option value="active" ${filters.filter === 'active' ? 'selected' : ''}>Active only</option>
          <option value="Awaiting Approval" ${filters.filter === 'Awaiting Approval' ? 'selected' : ''}>Awaiting approval</option>
          <option value="Escalated" ${filters.filter === 'Escalated' ? 'selected' : ''}>Escalated</option>
          <option value="Resolved" ${filters.filter === 'Resolved' ? 'selected' : ''}>Resolved</option>
        </select>
        <select id="risk-filter" aria-label="Filter cases by risk level">
          <option value="all" ${filters.risk === 'all' ? 'selected' : ''}>All risk levels</option>
          <option value="low" ${filters.risk === 'low' ? 'selected' : ''}>Low risk</option>
          <option value="medium" ${filters.risk === 'medium' ? 'selected' : ''}>Medium risk</option>
          <option value="high" ${filters.risk === 'high' ? 'selected' : ''}>High risk</option>
        </select>
      </div>
    </div>

    <div class="panel table-wrap">
      <table class="case-table" aria-label="Resolution cases list">
        <thead>
          <tr>
            <th>Case ID</th>
            <th>Customer</th>
            <th>Issue / Goal</th>
            <th>Status</th>
            <th>Risk</th>
            <th>Updated</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          ${shown.length ? shown.map(c => `
            <tr data-case="${c.id}" class="${c.id === selectedCaseId ? 'selected' : ''}" tabindex="0" role="button">
              <td><button class="case-link" data-action="select" data-id="${c.id}">CASE ${c.id}</button></td>
              <td>
                <div class="customer">
                  ${avatarHelper(c.customer, c.tone)}
                  <span>${esc(c.customer)}</span>
                </div>
              </td>
              <td>${esc(c.issue)}</td>
              <td>${badgeHelper(c.status)}</td>
              <td><span class="risk ${c.risk.toLowerCase()}"><span class="dot"></span>${esc(c.risk)}</span></td>
              <td style="color: var(--muted); font-size: 12px;">${agoHelper(c.updated)}</td>
              <td style="color: var(--muted);">${iconHelper('right')}</td>
            </tr>
          `).join('') : `
            <tr>
              <td colspan="7" style="text-align: center; color: var(--muted); padding: 36px;">
                No cases matched your criteria.
              </td>
            </tr>
          `}
        </tbody>
      </table>
      <div class="table-footer">
        <span>Showing ${shown.length} of ${list.length} cases</span>
        <span>Click any row to inspect trace & evidence</span>
      </div>
    </div>
  `;
}

/* Users Component: Personas & Governance Configuration */

export const PERSONAS = {
  manager: {
    key: 'manager',
    name: 'Alex Morgan',
    initials: 'AM',
    role: 'Resolution Operations Lead',
    department: 'Autonomous Resolution Operations',
    email: 'alex.morgan@novacart.internal',
    tone: '',
    level: 'Lead Admin (Level 3)',
    permissions: 'Autonomous Policy Tuning · High-Risk Signoff · Threshold Override',
    greeting: 'NOVACART · RESOLUTION OPERATIONS',
    dashboardTitle: 'Alex Morgan · Operations Workspace',
    badgeText: 'Lead Operations Manager',
    chipBadge: 'Manager',
    defaultCase: 'NR-1024'
  },
  specialist: {
    key: 'specialist',
    name: 'Priya Sharma',
    initials: 'PS',
    role: 'Tier-2 Dispute Specialist',
    department: 'Fraud & Escalations Desk',
    email: 'priya.sharma@novacart.internal',
    tone: 'mauve',
    level: 'Specialist (Level 2)',
    permissions: 'Evidence Inspection · Logistics Forensics · Exception Approval',
    greeting: 'NOVACART · FRAUD & DISPUTE DESK',
    dashboardTitle: 'Priya Sharma · Dispute Specialist Desk',
    badgeText: 'Dispute Specialist',
    chipBadge: 'Specialist',
    defaultCase: 'NR-1025'
  },
  customer: {
    key: 'customer',
    name: 'Rahul Sharma',
    initials: 'RS',
    role: 'Customer Portal View',
    department: 'Customer Account #NC-48391',
    email: 'rahul.sharma@example.com',
    tone: 'sand',
    level: 'End User Observer',
    permissions: 'Live Replacement Observability · Evidence Transparency',
    greeting: 'NOVACART · CUSTOMER SELF-SERVICE PORTAL',
    dashboardTitle: 'Rahul Sharma · Live Resolution Tracking',
    badgeText: 'Customer Self-Service',
    chipBadge: 'Customer',
    defaultCase: 'NR-1024'
  }
};

export function renderPersonaPopover(activePersonaKey, iconHelper) {
  return `
    <div class="popover persona-popover" role="dialog" aria-label="Switch User Persona">
      <div class="popover-title">
        <span>Switch User Persona</span>
      </div>
      <div class="persona-menu-list">
        ${Object.values(PERSONAS).map(p => `
          <button class="persona-menu-item ${activePersonaKey === p.key ? 'active' : ''}" data-action="select-persona-quick" data-persona="${p.key}">
            <span class="avatar ${p.tone}">${p.initials}</span>
            <div class="persona-menu-info">
              <strong>${p.name}</strong>
              <small>${p.role} · ${p.department}</small>
            </div>
            ${activePersonaKey === p.key ? iconHelper('circleCheck', 'check-icon') : ''}
          </button>
        `).join('')}
      </div>
      <div class="popover-footer">
        <button class="text-button" data-action="profile">${iconHelper('sliders')} Governance & Preferences</button>
      </div>
    </div>
  `;
}

export function renderPreferencesModal(activePersonaKey, threshold, autoReroute, focusMode, currentTheme, moneyHelper, avatarHelper, iconHelper, casesOverThreshold) {
  const p = PERSONAS[activePersonaKey] || PERSONAS.manager;
  return {
    title: 'Workspace Preferences & Governance Policies',
    body: `
      <div style="display: flex; gap: 14px; align-items: center; padding: 14px; background: var(--surface-subtle); border-radius: 10px; border: 1px solid var(--line);">
        ${avatarHelper(p.name, p.tone)}
        <div style="flex: 1; min-width: 0;">
          <div style="display: flex; align-items: center; gap: 8px;">
            <strong style="font-size: 14px; font-family: var(--font-display);">${p.name}</strong>
            <span class="badge blue">${p.level}</span>
          </div>
          <small style="color: var(--muted); display: block;">${p.email} · ${p.department}</small>
          <small style="color: var(--accent); font-size: 11px; margin-top: 2px; display: block;">${p.permissions}</small>
        </div>
      </div>

      <label style="margin-top: 18px;">Switch Active Persona (Demonstration)</label>
      <div class="persona-switcher">
        <div class="persona-card ${activePersonaKey === 'manager' ? 'active' : ''}" data-action="set-persona" data-persona="manager">
          ${avatarHelper('Alex Morgan', '')}
          <strong>Alex Morgan</strong>
          <small>Operations Lead</small>
        </div>
        <div class="persona-card ${activePersonaKey === 'specialist' ? 'active' : ''}" data-action="set-persona" data-persona="specialist">
          ${avatarHelper('Priya Sharma', 'mauve')}
          <strong>Priya Sharma</strong>
          <small>Dispute Specialist</small>
        </div>
        <div class="persona-card ${activePersonaKey === 'customer' ? 'active' : ''}" data-action="set-persona" data-persona="customer">
          ${avatarHelper('Rahul Sharma', 'sand')}
          <strong>Rahul Sharma</strong>
          <small>Customer View</small>
        </div>
      </div>

      <div class="slider-container">
        <div class="slider-header">
          <div>
            <label style="margin: 0; font-size: 13px;">Autonomous Approval Ceiling</label>
            <small style="color: var(--muted); display: block;">Refunds exceeding this value require manual manager sign-off.</small>
          </div>
          <strong id="threshold-val" style="font-family: var(--font-mono);">${moneyHelper(threshold)}</strong>
        </div>
        <input type="range" class="range-slider" id="threshold-range" min="2000" max="25000" step="500" value="${threshold}">
        <div class="range-meta">
          <span>₹2,000 (Conservative)</span>
          <span id="threshold-impact-badge" style="font-weight: 600; color: var(--accent);">${casesOverThreshold} cases require oversight</span>
          <span>₹25,000 (Aggressive)</span>
        </div>
      </div>

      <label>Operational Governance Policies</label>
      <div class="toggle-row">
        <div class="toggle-label">
          <strong>Autonomous Inventory Rerouting</strong>
          <small>Automatically search secondary warehouses when primary stock is zero</small>
        </div>
        <label class="switch">
          <input type="checkbox" id="reroute-toggle" ${autoReroute ? 'checked' : ''}>
          <span class="switch-slider"></span>
        </label>
      </div>

      <div class="toggle-row">
        <div class="toggle-label">
          <strong>Spotlight Focus Mode</strong>
          <small>Dim canvas background when inspecting decisions or replans (Shortcut: F)</small>
        </div>
        <label class="switch">
          <input type="checkbox" id="focus-toggle" ${focusMode ? 'checked' : ''}>
          <span class="switch-slider"></span>
        </label>
      </div>

      <label style="margin-top: 16px;">Interface Appearance</label>
      <div class="theme-selector-grid">
        <button class="theme-btn ${currentTheme === 'light' ? 'active' : ''}" data-action="set-theme-mode" data-theme="light">
          ${iconHelper('sun')} Light
        </button>
        <button class="theme-btn ${currentTheme === 'dark' ? 'active' : ''}" data-action="set-theme-mode" data-theme="dark">
          ${iconHelper('moon')} Dark
        </button>
        <button class="theme-btn" data-action="toggle-theme">
          ${iconHelper('refresh')} Toggle
        </button>
      </div>
    `,
    actions: `
      <button class="button" data-action="close-dialog">Cancel</button>
      <button class="button primary" data-action="save-preferences">Apply & Save</button>
    `
  };
}

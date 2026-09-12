/* NovaResolve Core Application Controller */

import { renderSidebarHtml, syncSidebarActive } from './components/navigation/navigation.js';
import { PERSONAS, renderPersonaPopover, renderPreferencesModal } from './components/users/users.js';
import { renderHeadingHtml, renderMetricsCards } from './components/metrics/metrics.js';
import { renderCasePanelHtml } from './components/case-panel/case-panel.js';
import { getCaseSteps, renderTraceHtml, renderEvidenceHtml, renderVerificationHtml } from './components/verification/verification.js';
import { renderApprovalPanel, renderContextPanel, renderCustomerSidePanel } from './components/approvals/approvals.js';
import { renderCaseQueueHtml } from './components/case-queue/case-queue.js';

// SVG Icon Paths Registry
const paths = {
  logo: 'M6 22V6h4.5l7 10.5V6H22v16h-4.5L10.5 11.5V22z',
  grid: 'M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z',
  cases: 'M3 7h7l2 2h9v11H3z M3 7V4h7l2 3',
  shield: 'M12 3l8 3v6c0 5-8 9-8 9s-8-4-8-9V6z M8 12l3 3 5-6',
  users: 'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2 M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8 M17 4a4 4 0 0 1 0 8 M22 21v-2a4 4 0 0 0-3-3.87',
  activity: 'M3 12h4l3-8 4 16 3-8h4',
  search: 'M21 21l-5-5 M10.5 18a7.5 7.5 0 1 0 0-15 7.5 7.5 0 0 0 0 15',
  bell: 'M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9 M10 21h4',
  right: 'M9 5l7 7-7 7',
  down: 'M6 9l6 6 6-6',
  arrow: 'M4 12h16 M14 6l6 6-6 6',
  check: 'M5 12l4 4L19 6',
  circleCheck: 'M22 11v1a10 10 0 1 1-6-9 M22 4L12 14l-3-3',
  refresh: 'M20 7v5h-5 M4 17v-5h5 M6.1 6.1a8 8 0 0 1 13.2 3 M4.7 14.9a8 8 0 0 0 13.2 3',
  warning: 'M12 3L2 21h20z M12 9v5 M12 17h.01',
  clock: 'M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0 M12 6v6l4 2',
  play: 'M7 4l14 8-14 8z',
  pause: 'M8 5v14 M16 5v14',
  x: 'M6 6l12 12 M6 18L18 6',
  package: 'M12 3l9 5-9 5-9-5z M3 8v10l9 5 9-5V8 M12 13v10 M7 5l10 5',
  file: 'M14 2H5v20h14V7z M14 2v6h5 M8 12h8 M8 16h6',
  bolt: 'M13 2L3 14h8l-1 8 11-13h-8z',
  layers: 'M12 3L2 8l10 5 10-5z M2 12l10 5 10-5 M2 16l10 5 10-5',
  route: 'M5 5h10a4 4 0 0 1 0 8H9a4 4 0 0 0 0 8h10 M16 18l3 3-3 3 M5 2a3 3 0 1 0 0 6 3 3 0 0 0 0-6',
  menu: 'M4 6h16 M4 12h16 M4 18h16',
  dots: 'M5 12h.01 M12 12h.01 M19 12h.01',
  external: 'M14 3h7v7 M21 3L10 14 M10 3H3v18h18v-7',
  inbox: 'M4 4h16l2 12v4H2v-4z M2 15h6l2 3h4l2-3h6',
  sliders: 'M4 6h8 M16 6h4 M4 18h4 M12 18h8 M12 3v6 M8 15v6',
  database: 'M20 5c0 2-4 3-8 3s-8-1-8-3 4-3 8-3 8 1 8 3z M4 5v14c0 2 4 3 8 3s8-1 8-3V5 M4 12c0 2 4 3 8 3s8-1 8-3',
  lock: 'M5 10h14v11H5z M8 10V6a4 4 0 0 1 8 0v4',
  sun: 'M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z',
  moon: 'M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z',
  focus: 'M12 2a10 10 0 1010 10A10 10 0 0012 2zm0 15a5 5 0 115-5 5 5 0 01-5 5zm0-3a2 2 0 102-2 2 2 0 00-2 2z'
};

const icon = (name, cls = '') => `<svg class="${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${paths[name] || paths.file}"/></svg>`;
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const initials = name => name.split(' ').map(s => s[0]).slice(0, 2).join('');
const money = n => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(n);
const now = Date.now();
const terminal = ['Resolved', 'Escalated', 'Failed'];

const statuses = {
  Investigating: ['blue', 'search'],
  Planning: ['blue', 'layers'],
  'Awaiting Approval': ['amber', 'shield'],
  Executing: ['blue', 'bolt'],
  Replanning: ['amber', 'refresh'],
  Verifying: ['blue', 'shield'],
  Resolved: ['green', 'circleCheck'],
  Escalated: ['red', 'external'],
  Failed: ['red', 'x']
};

const badge = status => {
  const [color, symbol] = statuses[status] || ['', 'clock'];
  return `<span class="badge ${color}">${icon(symbol)}${esc(status)}</span>`;
};
const avatar = (name, tone = '') => `<span class="avatar ${tone}" aria-hidden="true">${initials(name)}</span>`;
const ago = t => {
  const seconds = Math.max(0, Math.floor((Date.now() - t) / 1000));
  return seconds < 60 ? 'Just now' : seconds < 3600 ? `${Math.floor(seconds / 60)} min ago` : `${Math.floor(seconds / 3600)} hr ago`;
};

// Application State
let activePersona = 'manager';
let autonomousThreshold = 10000;
let autoRerouteEnabled = true;
let focusMode = false;
let currentTheme = localStorage.getItem('novaresolve-theme') || 'light';
document.documentElement.setAttribute('data-theme', currentTheme);

function createDemoCases() {
  return [
    { id: 'NR-1024', customer: 'Rahul Sharma', email: 'rahul.sharma@example.com', issue: 'Damaged product', goal: 'Damaged product · replacement requested', status: 'Replanning', risk: 'Low', resolution: 'Replacement', amount: 3499, order: 'NC-48391', product: 'NovaSound wireless headphones', warehouse: 'Delhi', alternate: 'Jaipur', stock: 4, updated: now - 32000, tone: '', reason: 'Original fulfillment warehouse has no available inventory.', recommendation: 'Route the replacement through an alternative warehouse.', verified: false, stage: 5 },
    { id: 'NR-1025', customer: 'Priya Mehta', email: 'priya.mehta@example.com', issue: 'Refund requested', goal: 'Return received · refund requested', status: 'Awaiting Approval', risk: 'High', resolution: 'Refund', amount: 12450, order: 'NC-48386', product: 'NovaView 27-inch monitor', updated: now - 120000, tone: 'mauve', reason: `Refund amount exceeds the ${money(autonomousThreshold)} autonomous approval threshold.`, recommendation: 'Approve the full refund. The returned item has been received and inspected.', verified: false },
    { id: 'NR-1035', customer: 'Diya Nair', email: 'diya.nair@example.com', issue: 'Refund requested', goal: 'Return received · refund requested', status: 'Awaiting Approval', risk: 'High', resolution: 'Refund', amount: 18990, order: 'NC-48355', product: 'NovaClean robot vacuum', updated: now - 420000, tone: '', reason: `Refund amount exceeds the ${money(autonomousThreshold)} autonomous approval threshold.`, recommendation: 'Approve the refund. Return eligibility and receipt have been confirmed.', verified: false },
    { id: 'NR-1026', customer: 'Aman Verma', email: 'aman.verma@example.com', issue: 'Order cancellation', goal: 'Cancel order before dispatch', status: 'Investigating', risk: 'Low', resolution: 'Cancellation', amount: 2199, order: 'NC-48394', product: 'NovaCharge charging station', updated: now - 180000, tone: 'blue', reason: 'Checking the shipment state before confirming cancellation.', recommendation: 'Inspect dispatch status and cancellation policy.', verified: false },
    { id: 'NR-1027', customer: 'Sneha Patel', email: 'sneha.patel@example.com', issue: 'Missing item', goal: 'Missing item · replacement requested', status: 'Executing', risk: 'Low', resolution: 'Replacement', amount: 1499, order: 'NC-48374', product: 'NovaFit activity band', warehouse: 'Mumbai', updated: now - 300000, tone: 'sand', reason: 'Replacement approved. Reserving one unit at the Mumbai warehouse.', recommendation: 'Create the replacement and verify the reservation.', verified: false },
    { id: 'NR-1028', customer: 'Arjun Reddy', email: 'arjun.reddy@example.com', issue: 'Delivery dispute', goal: 'Delivered parcel not received', status: 'Escalated', risk: 'Medium', resolution: 'Manual review', amount: 7999, order: 'NC-48361', product: 'NovaTab tablet', updated: now - 540000, tone: 'blue', reason: 'Carrier delivery evidence conflicts with the customer report.', recommendation: 'A resolution specialist must review proof of delivery.', verified: false },
    { id: 'NR-1029', customer: 'Ananya Iyer', email: 'ananya.iyer@example.com', issue: 'Refund requested', goal: 'Return accepted · refund completed', status: 'Resolved', risk: 'Low', resolution: 'Refund', amount: 2499, order: 'NC-48343', product: 'NovaKeys keyboard', updated: now - 720000, tone: 'mauve', reason: 'Refund completed and verified against the payment record.', recommendation: 'No further action required.', verified: true },
    { id: 'NR-1030', customer: 'Vikram Singh', email: 'vikram.singh@example.com', issue: 'Wrong item received', goal: 'Correct product replacement completed', status: 'Resolved', risk: 'Low', resolution: 'Replacement', amount: 3299, order: 'NC-48334', product: 'NovaSound speaker', updated: now - 1080000, tone: 'sand', reason: 'Replacement and inventory reservation verified.', recommendation: 'No further action required.', verified: true },
    { id: 'NR-1031', customer: 'Ishita Rao', email: 'ishita.rao@example.com', issue: 'Order cancellation', goal: 'Order cancellation completed', status: 'Resolved', risk: 'Low', resolution: 'Cancellation', amount: 1899, order: 'NC-48322', product: 'NovaLight desk lamp', updated: now - 1620000, tone: '', reason: 'Order cancellation confirmed. Payment reversal verified.', recommendation: 'No further action required.', verified: true },
    { id: 'NR-1032', customer: 'Rohan Kapoor', email: 'rohan.kapoor@example.com', issue: 'Damaged product', goal: 'Damaged product · refund requested', status: 'Planning', risk: 'Medium', resolution: 'Refund', amount: 6799, order: 'NC-48401', product: 'NovaHome air purifier', updated: now - 240000, tone: 'blue', reason: 'Evidence collected. Comparing eligible resolution options.', recommendation: 'Evaluate the refund against the return policy.', verified: false },
    { id: 'NR-1034', customer: 'Karan Shah', email: 'karan.shah@example.com', issue: 'Missing accessory', goal: 'Missing accessory · replacement created', status: 'Verifying', risk: 'Low', resolution: 'Replacement', amount: 799, order: 'NC-48389', product: 'NovaCharge USB-C adapter', warehouse: 'Bengaluru', updated: now - 60000, tone: 'sand', reason: 'Replacement created. Checking the reserved quantity and fulfillment record.', recommendation: 'Resolve only after the observed state matches the expected state.', verified: false }
  ];
}

let cases = createDemoCases();
const state = { view: 'overview', selected: 'NR-1024', tab: 'trace', filter: 'all', risk: 'all', query: '', limit: 6, playing: false, expanded: new Set(), popover: null };
let replayTimer, toastTimer, burstTimer;

const caseById = id => cases.find(c => c.id === id);
const selected = () => caseById(state.selected) || cases[0];
const pending = () => cases.filter(c => c.status === 'Awaiting Approval');
const pageNames = { overview: 'Overview', cases: 'Cases', approvals: 'Approvals', customers: 'Customers', activity: 'Activity' };

// View Renderers
function renderOverviewView() {
  const p = PERSONAS[activePersona];
  const activeCount = cases.filter(c => !terminal.includes(c.status)).length;
  let subtitle = activePersona === 'manager'
    ? `${activeCount} cases in motion. ${pending().length} decisions need your attention.`
    : activePersona === 'specialist'
    ? 'Tier-2 Escalations Queue · 3 priority investigations assigned to your desk.'
    : 'Order #NC-48391 · NovaSound wireless headphones · Live autonomous replacement tracking.';

  const replayBtn = `
    <button class="button primary" data-action="replay">
      ${icon(state.playing ? 'pause' : 'play')}
      <span>${state.playing ? 'Pause replay' : 'Replay demo'}</span>
    </button>
    <span class="demo-tag"><span class="dot"></span>Demo data</span>
  `;

  const steps = getCaseSteps(selected(), state.playing, money, p.name);
  let tabsHtml = '';
  if (state.tab === 'trace') tabsHtml = renderTraceHtml(selected(), steps, state.expanded, state.playing, icon, esc);
  else if (state.tab === 'evidence') tabsHtml = renderEvidenceHtml(selected(), icon, esc);
  else tabsHtml = renderVerificationHtml(selected(), icon, esc);

  return `
    ${renderHeadingHtml(p.dashboardTitle, subtitle, p, replayBtn, state.view, esc)}
    ${renderMetricsCards(activePersona, cases, pending(), terminal, icon)}
    <div class="section-label">
      <h2>${activePersona === 'customer' ? 'Your live resolution tracking' : terminal.includes(selected().status) ? 'Resolution detail' : 'The agent at work'}</h2>
      <span class="right-label">${icon('activity')}${activePersona === 'customer' ? 'Real-time agent routing & verification' : 'Follow the thinking. See the outcome.'}</span>
    </div>
    <div class="work-grid">
      <div id="case-panel-wrapper">${renderCasePanelHtml(selected(), state.tab, state.playing, focusMode, badge, avatar, icon, esc, tabsHtml)}</div>
      <aside class="side-stack" aria-label="Human oversight">
        ${activePersona === 'customer' ? renderCustomerSidePanel(icon) : `
          ${renderApprovalPanel(pending()[0], pending().length, money, avatar, icon, esc)}
          ${renderContextPanel(icon)}
        `}
        <div class="trust-note">
          ${icon('shield')}
          <span>${activePersona === 'customer' ? 'NovaCart Autonomous Resolution Guarantee: transparent evidence and zero customer fees.' : 'Actions are checked against policy and risk. A case is resolved only after verification.'}</span>
        </div>
      </aside>
    </div>
    ${activePersona === 'customer' ? '' : `<section class="queue-section" aria-label="Case queue">${renderCaseQueueHtml(cases, state.selected, state, badge, avatar, icon, ago, esc)}</section>`}
  `;
}

function renderCasesView() {
  const p = PERSONAS[activePersona];
  return `
    ${renderHeadingHtml('Case Directory', 'Filter and inspect all customer resolutions across NovaCart.', p, '', state.view, esc)}
    <section class="queue-section" style="margin-top: 0;" aria-label="All cases">
      ${renderCaseQueueHtml(cases, state.selected, { ...state, limit: 50 }, badge, avatar, icon, ago, esc)}
    </section>
  `;
}

function renderApprovalsView() {
  const p = PERSONAS[activePersona];
  const list = pending();
  return `
    ${renderHeadingHtml('Approval Queue', 'High-risk and out-of-threshold resolutions requiring human sign-off.', p, '', state.view, esc)}
    <div class="approvals-grid">
      ${list.length ? list.map(c => renderApprovalPanel(c, list.length, money, avatar, icon, esc)).join('') : `
        <div class="panel" style="padding: 40px; text-align: center; color: var(--muted); grid-column: span 2;">
          ${icon('circleCheck')}
          <p style="margin-top: 8px;">All pending decisions have been approved or reviewed.</p>
        </div>
      `}
    </div>
  `;
}

function renderCustomersView() {
  const p = PERSONAS[activePersona];
  return `
    ${renderHeadingHtml('Customer Accounts', 'Customer dispute histories and lifetime loyalty profiles.', p, '', state.view, esc)}
    <div class="approvals-grid">
      ${[
        { name: 'Rahul Sharma', email: 'rahul.sharma@example.com', orders: 12, tier: 'Gold Loyalty', tone: 'sand' },
        { name: 'Priya Mehta', email: 'priya.mehta@example.com', orders: 4, tier: 'Standard', tone: 'mauve' },
        { name: 'Diya Nair', email: 'diya.nair@example.com', orders: 8, tier: 'Platinum Member', tone: '' }
      ].map(cust => `
        <div class="panel" style="padding: 20px;">
          <div style="display: flex; gap: 12px; align-items: center; margin-bottom: 12px;">
            ${avatar(cust.name, cust.tone)}
            <div>
              <strong style="font-size: 14px; display: block; font-family: var(--font-display);">${cust.name}</strong>
              <small style="color: var(--muted);">${cust.email}</small>
            </div>
            <span class="badge blue" style="margin-left: auto;">${cust.tier}</span>
          </div>
          <p style="font-size: 12.5px; color: var(--muted); margin: 0;">Total verified lifetime orders: <strong>${cust.orders}</strong></p>
        </div>
      `).join('')}
    </div>
  `;
}

function renderActivityView() {
  const p = PERSONAS[activePersona];
  return `
    ${renderHeadingHtml('Autonomous Activity Trace', 'Real-time telemetry and state transitions executed by NovaResolve.', p, '', state.view, esc)}
    <div class="panel" style="padding: 22px;">
      <div style="display: flex; flex-direction: column; gap: 14px;">
        ${cases.slice(0, 6).map(c => `
          <div style="display: flex; align-items: center; gap: 14px; border-bottom: 1px solid var(--line); padding-bottom: 12px;">
            <span class="badge blue">${c.id}</span>
            <div style="flex: 1;">
              <strong style="font-size: 13.5px; font-family: var(--font-display);">${esc(c.goal)}</strong>
              <small style="color: var(--muted); display: block;">${esc(c.reason)}</small>
            </div>
            <span style="font-size: 11.5px; font-family: var(--font-mono); color: var(--muted);">${ago(c.updated)}</span>
          </div>
        `).join('')}
      </div>
    </div>
  `;
}

// Global Re-render Pipeline
export function render() {
  const p = PERSONAS[activePersona];
  const sidebar = document.getElementById('sidebar');
  if (sidebar) {
    sidebar.innerHTML = renderSidebarHtml(state.view, pending().length, p, icon, avatar);
    syncSidebarActive(state.view);
  }

  document.getElementById('breadcrumb-title').textContent = pageNames[state.view] || 'Overview';
  document.title = `NovaResolve · ${pageNames[state.view] || 'Overview'}`;

  // Topbar Updates
  const themeBtn = document.getElementById('theme-button');
  if (themeBtn) themeBtn.innerHTML = icon(currentTheme === 'dark' ? 'sun' : 'moon');
  const focusBtn = document.getElementById('focus-button');
  if (focusBtn) {
    focusBtn.innerHTML = icon('focus');
    focusBtn.classList.toggle('active', focusMode);
  }
  const topAvatar = document.getElementById('topbar-avatar');
  if (topAvatar) {
    topAvatar.textContent = p.initials;
    topAvatar.className = `avatar ${p.tone}`;
  }
  const chipAvatar = document.getElementById('chip-avatar');
  if (chipAvatar) {
    chipAvatar.textContent = p.initials;
    chipAvatar.className = `avatar-sm ${p.tone}`;
  }
  const chipName = document.getElementById('chip-name');
  if (chipName) chipName.textContent = p.name;
  const chipBadge = document.getElementById('chip-badge');
  if (chipBadge) chipBadge.textContent = p.chipBadge;
  const chipChevron = document.getElementById('chip-chevron');
  if (chipChevron) chipChevron.innerHTML = icon('down');

  const notifBtn = document.getElementById('notification-button');
  if (notifBtn) {
    notifBtn.innerHTML = icon('bell') + (pending().length ? '<span class="unread"></span>' : '');
  }

  const main = document.getElementById('main');
  const views = { overview: renderOverviewView, cases: renderCasesView, approvals: renderApprovalsView, customers: renderCustomersView, activity: renderActivityView };
  main.innerHTML = (views[state.view] || renderOverviewView)() + `
    <footer class="footer">
      <span class="row">${icon('shield')} NovaResolve · Autonomous customer resolution architecture</span>
      <span>Demo workspace · Simulated production data</span>
    </footer>
  `;
}

export function switchPersona(personaKey) {
  if (!PERSONAS[personaKey]) return;
  activePersona = personaKey;
  const p = PERSONAS[activePersona];
  if (p.defaultCase && caseById(p.defaultCase)) {
    state.selected = p.defaultCase;
  }
  closePopover();
  const dlg = document.getElementById('dialog');
  if (dlg && dlg.open) dlg.close();
  render();
  toast(`Active persona switched to ${p.name} (${p.role}).`);
}

export function toggleFocusMode() {
  focusMode = !focusMode;
  document.body.classList.toggle('focus-mode-active', focusMode);
  const btn = document.getElementById('focus-button');
  if (btn) btn.classList.toggle('active', focusMode);
  render();
  if (focusMode) {
    setTimeout(() => {
      const target = document.querySelector('.spotlight-focus-target') || document.getElementById('case-panel');
      if (target) {
        const topbar = document.querySelector('.topbar');
        const offset = (topbar ? topbar.offsetHeight : 64) + 16;
        const targetTop = target.getBoundingClientRect().top + window.pageYOffset - offset;
        window.scrollTo({ top: Math.max(0, targetTop), behavior: 'smooth' });
      }
    }, 50);
  }
  toast(focusMode ? 'Spotlight Focus Mode activated. Press Esc to exit.' : 'Focus Mode deactivated.');
}

export function toggleTheme(forced) {
  currentTheme = forced || (currentTheme === 'dark' ? 'light' : 'dark');
  document.documentElement.setAttribute('data-theme', currentTheme);
  localStorage.setItem('novaresolve-theme', currentTheme);
  render();
  toast(`Switched to ${currentTheme === 'dark' ? 'Dark' : 'Light'} theme.`);
}

export function toast(message) {
  clearTimeout(toastTimer);
  const el = document.getElementById('toast');
  el.innerHTML = icon('circleCheck') + `<span>${esc(message)}</span>`;
  el.hidden = false;
  toastTimer = setTimeout(() => { el.hidden = true; }, 4000);
}

export function closePopover() {
  state.popover = null;
  document.getElementById('popover-root').innerHTML = '';
}

export function runReplay() {
  const c = caseById('NR-1024');
  if (!c) return;
  state.selected = 'NR-1024';
  state.tab = 'trace';
  state.playing = !state.playing;

  if (state.playing) {
    c.stage = 0;
    c.status = 'Investigating';
    c.reason = 'Customer identified. Inspecting order NC-48391.';
    render();
    clearInterval(replayTimer);
    replayTimer = setInterval(() => {
      c.stage++;
      if (c.stage === 4) { c.status = 'Replanning'; c.reason = 'Delhi inventory is 0. Searching alternative warehouse.'; }
      else if (c.stage === 6) { c.reason = 'Alternative found in Jaipur (4 units). Replanning route.'; }
      else if (c.stage === 7) { c.status = 'Executing'; c.reason = 'Reserving 1 unit at Jaipur warehouse.'; }
      else if (c.stage >= 8) {
        c.stage = 8;
        c.status = 'Resolved';
        c.verified = true;
        c.reason = 'Replacement created in Jaipur and verified against inventory record.';
        state.playing = false;
        clearInterval(replayTimer);
        toast('Autonomous replanning and independent verification completed.');
      }
      render();
    }, 1200);
  } else {
    clearInterval(replayTimer);
    render();
  }
}

// Global Event Listeners Setup
document.addEventListener('click', event => {
  const button = event.target.closest('[data-action]');
  if (!button) {
    const nav = event.target.closest('a[href^="#"]');
    if (nav && pageNames[nav.hash.slice(1)]) {
      event.preventDefault();
      state.view = nav.hash.slice(1);
      closePopover();
      render();
      window.scrollTo({ top: 0, behavior: 'instant' });
      return;
    }
    const row = event.target.closest('[data-case]');
    if (row) {
      state.selected = row.dataset.case;
      state.tab = 'trace';
      state.view = 'overview';
      render();
      return;
    }
    if (!event.target.closest('.popover')) closePopover();
    return;
  }

  const a = button.dataset.action;
  if (a === 'toggle-persona-popover') {
    if (state.popover === 'persona') { closePopover(); return; }
    state.popover = 'persona';
    document.getElementById('popover-root').innerHTML = renderPersonaPopover(activePersona, icon);
  }
  else if (a === 'select-persona-quick') switchPersona(button.dataset.persona);
  else if (a === 'set-persona') switchPersona(button.dataset.persona);
  else if (a === 'toggle-focus') toggleFocusMode();
  else if (a === 'exit-focus') { if (focusMode) toggleFocusMode(); }
  else if (a === 'toggle-theme') toggleTheme();
  else if (a === 'set-theme-mode') toggleTheme(button.dataset.theme);
  else if (a === 'profile') {
    closePopover();
    const modalData = renderPreferencesModal(
      activePersona,
      autonomousThreshold,
      autoRerouteEnabled,
      focusMode,
      currentTheme,
      money,
      avatar,
      icon,
      cases.filter(c => c.amount > autonomousThreshold).length
    );
    const dlg = document.getElementById('dialog');
    dlg.innerHTML = `
      <div class="dialog-header">
        <h2 style="font-size: 16px; margin: 0;">${modalData.title}</h2>
        <button class="icon-button" data-action="close-dialog">${icon('x')}</button>
      </div>
      <div class="dialog-body">${modalData.body}</div>
      <div class="dialog-actions">${modalData.actions}</div>
    `;
    dlg.showModal();
    const slider = document.getElementById('threshold-range');
    const valDisplay = document.getElementById('threshold-val');
    const badgeEl = document.getElementById('threshold-impact-badge');
    if (slider && valDisplay) {
      slider.addEventListener('input', e => {
        const val = Number(e.target.value);
        valDisplay.textContent = money(val);
        const over = cases.filter(c => c.amount > val).length;
        if (badgeEl) badgeEl.textContent = `${over} case${over === 1 ? '' : 's'} require oversight`;
      });
    }
  }
  else if (a === 'save-preferences') {
    const slider = document.getElementById('threshold-range');
    if (slider) autonomousThreshold = Number(slider.value);
    const reroute = document.getElementById('reroute-toggle');
    if (reroute) autoRerouteEnabled = reroute.checked;
    const focusCheck = document.getElementById('focus-toggle');
    if (focusCheck && focusCheck.checked !== focusMode) toggleFocusMode();
    document.getElementById('dialog').close();
    render();
    toast(`Autonomous threshold saved at ${money(autonomousThreshold)}.`);
  }
  else if (a === 'close-dialog') document.getElementById('dialog').close();
  else if (a === 'tab') { state.tab = button.dataset.tab; render(); }
  else if (a === 'step') {
    const key = `${selected().id}-${button.dataset.step}`;
    state.expanded.has(key) ? state.expanded.delete(key) : state.expanded.add(key);
    render();
  }
  else if (a === 'expand-all') {
    if (state.expanded.size) state.expanded.clear();
    else getCaseSteps(selected(), state.playing, money, PERSONAS[activePersona].name).forEach((s, i) => { if (s.state !== 'waiting') state.expanded.add(`${selected().id}-${i}`); });
    render();
  }
  else if (a === 'replay') runReplay();
  else if (a === 'review') {
    const c = caseById(button.dataset.id);
    const dec = button.dataset.decision;
    if (c) {
      c.decision = dec;
      c.status = dec === 'approve' ? 'Executing' : 'Escalated';
      c.reason = dec === 'approve' ? `Approved by ${PERSONAS[activePersona].name}. Autonomous refund executing.` : `Rejected by ${PERSONAS[activePersona].name}. Awaiting specialist review.`;
      render();
      toast(`Case ${c.id} marked as ${dec === 'approve' ? 'Approved' : 'Rejected'}.`);
    }
  }
  else if (a === 'metric') {
    state.filter = button.dataset.filter;
    state.risk = 'all';
    state.view = 'cases';
    render();
  }
  else if (a === 'select') {
    state.selected = button.dataset.id;
    state.view = 'overview';
    state.tab = 'trace';
    render();
  }
});

document.addEventListener('change', event => {
  if (event.target.id === 'status-filter') {
    state.filter = event.target.value;
    render();
  } else if (event.target.id === 'risk-filter') {
    state.risk = event.target.value;
    render();
  }
});

document.addEventListener('keydown', event => {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault();
    document.getElementById('global-search')?.focus();
  }
  if (event.key.toLowerCase() === 'f' && !['input', 'textarea', 'select'].includes(document.activeElement?.tagName?.toLowerCase())) {
    event.preventDefault();
    toggleFocusMode();
  }
  if (event.key === 'Escape') {
    if (focusMode) toggleFocusMode();
    if (state.popover) closePopover();
  }
});

window.addEventListener('popstate', () => {
  state.view = pageNames[location.hash.slice(1)] ? location.hash.slice(1) : 'overview';
  render();
});

// Initial boot
document.getElementById('menu-button').innerHTML = icon('menu');
document.getElementById('breadcrumb-chevron').innerHTML = icon('right');
document.getElementById('search-icon').innerHTML = icon('search');
state.view = pageNames[location.hash.slice(1)] ? location.hash.slice(1) : 'overview';
render();

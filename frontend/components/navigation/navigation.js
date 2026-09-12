/* Navigation Component: Sidebar & Topbar Logic */

export function renderSidebarHtml(activeView, pendingApprovalsCount, persona, iconHelper, avatarHelper) {
  const navItems = [
    ['overview', 'grid', 'Overview'],
    ['cases', 'cases', 'Cases'],
    ['approvals', 'shield', 'Approvals'],
    ['customers', 'users', 'Customers'],
    ['activity', 'activity', 'Activity']
  ];

  return `
    <a href="#overview" class="brand" aria-label="NovaResolve overview">
      <span class="brand-mark">${iconHelper('logo')}</span>
      <div class="brand-text">
        <span class="brand-name">NovaResolve</span>
        <span class="brand-description">Resolution, reimagined.</span>
      </div>
    </a>
    <div class="workspace">
      <span class="workspace-logo">${iconHelper('package')}</span>
      <div>
        <strong>NovaCart</strong>
        <small>Demo workspace</small>
      </div>
    </div>
    <div class="nav-label">WORKSPACE</div>
    <nav class="nav">
      <span class="nav-marker" aria-hidden="true"></span>
      ${navItems.map(([id, symbol, label]) => `
        <a href="#${id}" data-nav="${id}" class="${id === activeView ? 'active' : ''}">
          ${iconHelper(symbol)}
          <span>${label}</span>
          ${id === 'approvals' ? `<span class="count" id="approval-count" ${pendingApprovalsCount ? '' : 'hidden'}>${pendingApprovalsCount}</span>` : ''}
        </a>
      `).join('')}
    </nav>
    <div class="sidebar-bottom">
      <button class="system-link" data-action="system">
        <span class="dot"></span>
        <span>System status</span>
        ${iconHelper('right')}
      </button>
      <div class="sidebar-session">
        ${iconHelper('database')}
        <span>Simulated workspace</span>
      </div>
      <button class="profile" data-action="profile" aria-label="Open workspace preferences">
        ${avatarHelper(persona.name, persona.tone)}
        <div>
          <strong>${persona.name}</strong>
          <small>${persona.role}</small>
        </div>
        ${iconHelper('sliders')}
      </button>
    </div>
  `;
}

export function syncSidebarActive(activeView) {
  const sidebar = document.getElementById('sidebar');
  if (!sidebar) return;
  const links = sidebar.querySelectorAll('[data-nav]');
  const navItems = ['overview', 'cases', 'approvals', 'customers', 'activity'];
  const activeIndex = navItems.indexOf(activeView);
  
  links.forEach(link => {
    const isActive = link.dataset.nav === activeView;
    link.classList.toggle('active', isActive);
  });

  const marker = sidebar.querySelector('.nav-marker');
  if (marker && activeIndex >= 0) {
    marker.style.transform = `translateY(${activeIndex * 46}px)`;
  }
}

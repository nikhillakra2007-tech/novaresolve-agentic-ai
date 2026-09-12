/* Case Panel Component Logic with Interactive Route Matrix & Telemetry Scrubber */

export function renderCasePanelHtml(c, activeTab, isPlaying, focusMode, badgeHelper, avatarHelper, iconHelper, esc, tabsContentHtml, replaySpeed = 1) {
  const moving = (isPlaying && c.id === 'NR-1024') || (c.decision === 'approve' && ['Executing', 'Verifying'].includes(c.status));
  const activeLabel = moving ? 'Autonomous agent executing' : c.verified ? 'Verified state outcome' : ['Resolved', 'Escalated', 'Failed'].includes(c.status) ? 'Review the outcome' : 'CURRENT AGENT STATE';
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
    const dispatched = c.stage >= 7;
    routeHtml = `
      <div class="route-matrix" aria-label="Dynamic supply chain rerouting matrix">
        <div class="route-matrix-topline">
          <div class="route-matrix-title">
            ${iconHelper('route')}
            <span>Autonomous Supply Chain Reroute</span>
          </div>
          <span class="route-matrix-tag">${c.stage >= 8 ? 'Reroute Verified' : 'Real-time Spatial Query'}</span>
        </div>

        <div class="route-matrix-track">
          <!-- Step 1: Delhi -->
          <div class="route-step blocked">
            <div class="route-step-icon">${iconHelper('package')}</div>
            <div class="route-step-info">
              <span class="route-step-name">Delhi Hub</span>
              <span class="route-step-sub red">Stock: 0 · Blocked</span>
            </div>
          </div>

          <!-- Connector 1 -->
          <div class="route-track-connector ${moving ? 'moving' : ''}">
            <span class="track-badge">260 km Reroute</span>
            <div class="track-line"><span class="track-pulse"></span></div>
          </div>

          <!-- Step 2: Jaipur -->
          <div class="route-step ${found ? 'found' : 'pending'}">
            <div class="route-step-icon">${iconHelper(found ? 'circleCheck' : 'search')}</div>
            <div class="route-step-info">
              <span class="route-step-name">Jaipur Robotic Hub</span>
              <span class="route-step-sub ${found ? 'emerald' : 'muted'}">${dispatched ? '1 unit reserved' : found ? '4 units available' : 'Querying inventory'}</span>
            </div>
          </div>

          <!-- Connector 2 -->
          <div class="route-track-connector ${dispatched ? 'moving' : ''}">
            <span class="track-badge">Express</span>
            <div class="track-line"><span class="track-pulse"></span></div>
          </div>

          <!-- Step 3: Priority Dispatch -->
          <div class="route-step ${dispatched ? 'dispatched' : 'pending'}">
            <div class="route-step-icon">${iconHelper('route')}</div>
            <div class="route-step-info">
              <span class="route-step-name">Priority Dispatch</span>
              <span class="route-step-sub ${dispatched ? 'cyan' : 'muted'}">${dispatched ? 'Tracking #NE-9821' : 'Awaiting fulfillment'}</span>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  // Interactive step scrubber controls for demo or interactive cases
  let scrubberHtml = '';
  if (c.id === 'NR-1024') {
    scrubberHtml = `
      <div class="case-scrubber-bar" aria-label="Agent execution scrubber">
        <div class="scrubber-controls">
          <button class="scrub-btn" data-action="step-prev" title="Step Backward" ${c.stage <= 0 ? 'disabled' : ''}>
            ${iconHelper('arrow', 'rot-180')}
          </button>
          <button class="scrub-btn play-pause-btn ${isPlaying ? 'playing' : ''}" data-action="replay" title="${isPlaying ? 'Pause Agent' : 'Play / Replay Agent'}">
            ${iconHelper(isPlaying ? 'pause' : 'play')}
          </button>
          <button class="scrub-btn" data-action="step-next" title="Step Forward" ${c.stage >= 8 ? 'disabled' : ''}>
            ${iconHelper('arrow')}
          </button>
        </div>

        <div class="scrubber-slider-wrap">
          <div class="scrubber-label-row">
            <span><strong>Execution Timeline:</strong> Step ${(c.stage ?? 0) + 1} of 9</span>
            <span class="telemetry-pill">${c.stage >= 8 ? 'Verification Match: 100%' : c.stage >= 4 ? 'Spatial Re-planning' : 'Initial Trajectory'}</span>
          </div>
          <input type="range" class="scrubber-slider" id="scrubber-range" min="0" max="8" value="${c.stage ?? 0}" step="1" data-action="scrub-step">
        </div>

        <div class="scrubber-speed-pills">
          <button class="speed-pill ${replaySpeed === 1 ? 'active' : ''}" data-action="set-speed" data-speed="1">1x</button>
          <button class="speed-pill ${replaySpeed === 2 ? 'active' : ''}" data-action="set-speed" data-speed="2">2x</button>
          <button class="speed-pill ${replaySpeed === 4 ? 'active' : ''}" data-action="set-speed" data-speed="4">4x</button>
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
            <span class="telemetry-hud-badge">
              <span class="hud-dot"></span>
              Gemini 1.5 Pro Runtime
            </span>
          </div>
          <h2 class="case-title">${esc(c.goal)}</h2>
        </div>
        <div class="panel-header-actions">
          <button class="icon-button" data-action="quick-command" title="Open Command Palette (Ctrl+K)" aria-label="Open Command Palette">${iconHelper('search')}</button>
          <button class="icon-button" data-action="case-info" aria-label="View case information">${iconHelper('dots')}</button>
        </div>
      </div>

      <div class="case-goal">
        ${avatarHelper(c.customer, c.tone)}
        <div>
          <strong>${esc(c.customer)}</strong>
          <p>${esc(c.product)} · <em>Order #${c.order}</em></p>
        </div>
        <div class="goal-meta">
          <span>Resolution Budget</span>
          <strong>$${((c.amount || 0)).toFixed(2)}</strong>
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

      ${scrubberHtml}

      <div class="panel-tabs" role="tablist" aria-label="Case information tabs">
        ${[
          ['trace', 'activity', 'Execution trace'],
          ['evidence', 'file', 'Evidence forensic snapshot'],
          ['verification', 'shield', 'Zero-trust verification']
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

/* Command Palette Component Logic */

export function renderCommandPaletteHtml(query = '', items = [], selectedIndex = 0, iconHelper) {
  return `
    <div class="cmd-backdrop" id="cmd-backdrop" data-action="close-cmd">
      <div class="cmd-palette" onclick="event.stopPropagation()">
        <div class="cmd-input-wrap">
          ${iconHelper('search')}
          <input type="text" class="cmd-input" id="cmd-input" placeholder="Type a command, case ID, or customer name..." value="${query}" autocomplete="off" autofocus>
          <span class="cmd-badge">ESC to close</span>
        </div>
        <div class="cmd-results" id="cmd-results">
          ${items.length ? items.map((item, idx) => `
            ${item.group ? `<div class="cmd-group-label">${item.group}</div>` : ''}
            <button class="cmd-item ${idx === selectedIndex ? 'selected' : ''}" data-action="cmd-exec" data-cmd="${item.id}" data-param="${item.param || ''}">
              <span class="cmd-item-icon">${iconHelper(item.icon)}</span>
              <div class="cmd-item-info">
                <span class="cmd-item-title">${item.title}</span>
                ${item.desc ? `<span class="cmd-item-desc">${item.desc}</span>` : ''}
              </div>
              ${item.shortcut ? `<span class="cmd-item-kbd">${item.shortcut}</span>` : ''}
            </button>
          `).join('') : `
            <div style="padding: 28px; text-align: center; color: var(--muted); font-size: 13px;">
              No matching actions or cases found.
            </div>
          `}
        </div>
        <div class="cmd-footer">
          <span>NovaResolve Omni-Command System</span>
          <div class="cmd-footer-keys">
            <span><kbd>↑</kbd> <kbd>↓</kbd> Navigate</span>
            <span><kbd>↵</kbd> Execute</span>
          </div>
        </div>
      </div>
    </div>
  `;
}

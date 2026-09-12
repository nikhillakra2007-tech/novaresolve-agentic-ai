# NovaResolve — Autonomous Resolution Control Center Frontend

[![Live on Vercel](https://img.shields.io/badge/Vercel-Live%20Production-000000.svg?style=flat&logo=vercel)](https://novaresolve-agentic-ai.vercel.app)
[![Local Development](https://img.shields.io/badge/Local-127.0.0.1%3A3000-blue.svg?style=flat)](http://127.0.0.1:3000)
[![Repository](https://img.shields.io/badge/GitHub-novaresolve--agentic--ai-181717.svg?style=flat&logo=github)](https://github.com/nikhillakra2007-tech/novaresolve-agentic-ai)

The high-performance, modular UI powering the **NovaResolve Autonomous Agentic Customer Resolution Platform** for NovaCart.

---

## Live Links

- **Production URL**: [https://novaresolve-agentic-ai.vercel.app](https://novaresolve-agentic-ai.vercel.app)
- **GitHub Repository**: [https://github.com/nikhillakra2007-tech/novaresolve-agentic-ai](https://github.com/nikhillakra2007-tech/novaresolve-agentic-ai)
- **Local Dev Server**: `http://127.0.0.1:3000` (Reverse proxies `/api/` to backend on port 8000)

---

## Core Capabilities & Architecture

1. **Autonomous Supply Chain Re-Routing Matrix**
   - Visual spatial topology tracking real-time stockouts (e.g. Delhi Hub 0 units stockout) and autonomous spatial rerouting to regional robotic hubs (Jaipur Hub 4 units reserved) with animated express carrier dispatch.

2. **Interactive Mission Control Scrubber & Speed Controls**
   - Step-by-step scrubber slider enabling evaluators to jump forward/backward across all 9 agent reasoning stages.
   - Variable replay speed presets (`1x`, `2x`, `4x`).

3. **Sci-Fi Audio Feedback Engine (`sound.js`)**
   - Synthesizes futuristic micro-audio on-the-fly using the browser's native Web Audio API (zero external sound assets).
   - Radar blips on step execution, spatial chime on reroute, harmonic victory chord on resolution, and warning alerts on supervisor approval gates.

4. **Zero-Trust Parity Matrix (`verification.js`)**
   - Side-by-side ledger audit comparing Expected Target State against Observed Database Truth with cryptographic hash validation.

5. **Omni Command Palette (<kbd>Ctrl</kbd> + <kbd>K</kbd> / <kbd>⌘</kbd> + <kbd>K</kbd>)**
   - Instant keyboard-driven palette for lightning-fast case search, persona switching, and system actions.

6. **60 FPS Cyber Confetti Engine (`confetti.js`)**
   - Native HTML5 canvas physics particle explosion rewarding verified resolutions.

---

## Directory Structure

```
frontend/
├── index.html                   # HTML5 application shell & font preconnects
├── server.mjs                   # Lightweight zero-dependency HTTP & reverse proxy server
├── app.js                       # Core application state controller & event bus
├── sound.js                     # Native Web Audio API synthesizer
├── styles/
│   ├── global.css               # Design system tokens, cursor spotlight, glassmorphism
│   └── animations.css           # Keyframe animations, pulse rings, route laser travel
└── components/
    ├── case-panel/              # Work grid, case header, route matrix, scrubber
    ├── verification/            # Step-by-step trace, evidence snapshot, parity matrix
    ├── metrics/                 # KPI metric cards & live SVG sparklines
    ├── approvals/               # Human-in-the-loop signoff & context guarantees
    ├── case-queue/              # Filterable and searchable case directory table
    ├── command-palette/         # Quick omni-search modal & keyboard navigation
    ├── confetti.js              # Canvas particle celebration physics
    ├── navigation/              # Responsive sidebar, brand, and active indicator
    └── users/                   # Multi-persona engine (Alex Morgan / Priya Sharma / Rahul Sharma)
```

## Running Locally

```bash
cd frontend
node server.mjs
```
Open [http://127.0.0.1:3000](http://127.0.0.1:3000) in your browser.

(() => {
  const byId = id => document.getElementById(id);
  const canvas = byId('worldCanvas');
  const ctx = canvas.getContext('2d');

  const ui = {
    connection: byId('connectionState'),
    environment: byId('environmentName'),
    backend: byId('brainBackend'),
    title: byId('worldTitle'),
    runtimeState: byId('runtimeState'),
    episode: byId('episode'),
    action: byId('action'),
    reward: byId('reward'),
    event: byId('eventName'),
    brainMs: byId('brainMs'),
    computeSeconds: byId('computeSeconds'),
    totalSpikes: byId('totalSpikes'),
    gateSpikes: byId('gateSpikes'),
    sensory: byId('sensorySummary'),
    running: byId('running'),
    tickSeconds: byId('tickSeconds'),
    persistent: byId('persistent'),
    phase: byId('phase'),
  };

  const MODEL_NAMES = {
    'neurofly-maze-chase-v0.1': 'Maze Chase',
    'neurofly-light-chase-v0.1': 'Light Chase',
  };

  function finite(value) {
    const n = Number(value);
    return Number.isFinite(n) ? n : null;
  }

  function text(value, fallback = '—') {
    return value == null || value === '' ? fallback : String(value);
  }

  function rewardText(value) {
    const n = finite(value);
    return n == null ? '—' : `${n >= 0 ? '+' : ''}${n.toFixed(3)}`;
  }

  function drawBackground() {
    const gradient = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
    gradient.addColorStop(0, '#071711');
    gradient.addColorStop(1, '#020706');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
  }

  function drawMaze(state, arena) {
    drawBackground();
    const grid = Array.isArray(state.grid) ? state.grid : [];
    const cols = finite(arena?.cols) || 19;
    const rows = finite(arena?.rows) || 14;
    const cw = canvas.width / cols;
    const ch = canvas.height / rows;

    for (let y = 0; y < rows; y++) {
      const row = String(grid[y] || ''.padEnd(cols, '#'));
      for (let x = 0; x < cols; x++) {
        const cell = row[x];
        const px = x * cw;
        const py = y * ch;

        if (cell === '#') {
          ctx.fillStyle = '#17372e';
          ctx.fillRect(px + 2, py + 2, cw - 4, ch - 4);
        } else {
          ctx.fillStyle = (x + y) % 2 === 0 ? '#07130f' : '#091610';
          ctx.fillRect(px, py, cw, ch);
        }

        if (cell === '.' || cell === 'o') {
          ctx.beginPath();
          ctx.arc(px + cw / 2, py + ch / 2, cell === 'o' ? 6 : 3, 0, Math.PI * 2);
          ctx.fillStyle = cell === 'o' ? '#79cfff' : '#e8c959';
          ctx.fill();
        }
      }
    }

    for (const enemy of state.enemies || []) {
      ctx.beginPath();
      ctx.arc(
        Number(enemy.x) * cw + cw / 2,
        Number(enemy.y) * ch + ch / 2,
        Math.max(6, Math.min(cw, ch) * .28),
        0,
        Math.PI * 2,
      );
      ctx.fillStyle = '#ff6477';
      ctx.fill();
    }

    if (state.fly) {
      const fly = state.fly;
      ctx.beginPath();
      ctx.arc(
        Number(fly.x) * cw + cw / 2,
        Number(fly.y) * ch + ch / 2,
        Math.max(6, Math.min(cw, ch) * .25),
        0,
        Math.PI * 2,
      );
      ctx.fillStyle = '#d6ff73';
      ctx.fill();
    }
  }

  function drawLight(state, arena) {
    drawBackground();
    const cols = finite(arena?.cols) || 15;
    const rows = finite(arena?.rows) || 11;
    const margin = 44;
    const width = canvas.width - margin * 2;
    const height = canvas.height - margin * 2;
    const cw = width / Math.max(1, cols);
    const ch = height / Math.max(1, rows);

    ctx.strokeStyle = 'rgba(170, 219, 188, .15)';
    ctx.lineWidth = 1;
    ctx.strokeRect(margin, margin, width, height);

    for (let x = 1; x < cols; x++) {
      const px = margin + x * cw;
      ctx.beginPath();
      ctx.moveTo(px, margin);
      ctx.lineTo(px, margin + height);
      ctx.stroke();
    }
    for (let y = 1; y < rows; y++) {
      const py = margin + y * ch;
      ctx.beginPath();
      ctx.moveTo(margin, py);
      ctx.lineTo(margin + width, py);
      ctx.stroke();
    }

    if (state.target) {
      const x = margin + (Number(state.target.x) + .5) * cw;
      const y = margin + (Number(state.target.y) + .5) * ch;
      const radius = Math.max(9, Math.min(cw, ch) * .36);
      const glow = ctx.createRadialGradient(x, y, 0, x, y, radius * 3);
      glow.addColorStop(0, 'rgba(250, 249, 184, 1)');
      glow.addColorStop(.3, 'rgba(245, 235, 128, .65)');
      glow.addColorStop(1, 'rgba(245, 235, 128, 0)');
      ctx.fillStyle = glow;
      ctx.beginPath();
      ctx.arc(x, y, radius * 3, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = '#fffbc2';
      ctx.beginPath();
      ctx.arc(x, y, radius, 0, Math.PI * 2);
      ctx.fill();
    }

    if (state.agent) {
      const x = margin + (Number(state.agent.x) + .5) * cw;
      const y = margin + (Number(state.agent.y) + .5) * ch;
      ctx.save();
      ctx.translate(x, y);
      ctx.fillStyle = '#d6ff73';
      ctx.beginPath();
      ctx.arc(0, 0, Math.max(8, Math.min(cw, ch) * .26), 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = '#11301f';
      ctx.font = '700 12px system-ui';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(text(state.agent.dir, '?').slice(0, 1), 0, 1);
      ctx.restore();
    }
  }

  function drawUnsupported(model) {
    drawBackground();
    ctx.fillStyle = '#d6ff73';
    ctx.textAlign = 'center';
    ctx.font = '800 28px system-ui';
    ctx.fillText('Unsupported environment renderer', canvas.width / 2, canvas.height / 2 - 10);
    ctx.fillStyle = '#91a99a';
    ctx.font = '15px system-ui';
    ctx.fillText(text(model), canvas.width / 2, canvas.height / 2 + 24);
  }

  function sensorySummary(contract) {
    if (!contract || typeof contract !== 'object') return '尚未收到 sensory contract';

    const lines = [];
    const vision = contract.vision || {};
    if (vision.model) {
      lines.push(`Vision · ${vision.model}`);
      if (vision.coordinate_frame) lines.push(`視覺座標系 · ${vision.coordinate_frame}`);
    }

    const odor = contract.olfaction || {};
    if (odor.model) {
      const food = odor.food || {};
      const danger = odor.danger || {};
      const pct = value => {
        const n = finite(value);
        return n == null ? '—' : `${(Math.max(0, Math.min(1, n)) * 100).toFixed(1)}%`;
      };
      lines.push(`Olfaction · ${odor.model}`);
      lines.push(`Food L/R · ${pct(food.left)} / ${pct(food.right)}`);
      lines.push(`Danger L/R · ${pct(danger.left)} / ${pct(danger.right)}`);
    }

    if (!lines.length) lines.push('此 environment 目前只提供影像 sensory frame');
    return lines.join('\n');
  }

  function render(payload) {
    if (!payload || payload.schema !== 'neurofly-platform-live-state-v0.1') {
      throw new Error('unsupported platform state schema');
    }

    const state = payload.state || {};
    const runtime = payload.runtime || {};
    const brain = state.brain || {};
    const telemetry = brain.telemetry || {};
    const model = payload.environment_model;

    ui.environment.textContent = MODEL_NAMES[model] || text(model);
    ui.backend.textContent = text(payload.backend);
    ui.title.textContent = MODEL_NAMES[model] || text(model);
    ui.runtimeState.textContent = runtime.error ? `ERROR · ${runtime.error}` : text(runtime.phase);
    ui.episode.textContent = text(state.episode);
    ui.action.textContent = text(state.last_action || state.decision_action);
    ui.reward.textContent = rewardText(state.last_reward);
    ui.event.textContent = text(state.step_event || state.last_event);
    ui.brainMs.textContent = finite(telemetry.brain_ms) == null ? '—' : `${Number(telemetry.brain_ms).toFixed(1)} ms`;
    ui.computeSeconds.textContent = finite(telemetry.compute_seconds) == null ? '—' : `${Number(telemetry.compute_seconds).toFixed(3)} s`;
    ui.totalSpikes.textContent = text(telemetry.total_spikes);
    ui.gateSpikes.textContent = text(telemetry.gate_spikes);
    ui.sensory.textContent = sensorySummary(state.sensory_contract);
    ui.running.textContent = runtime.running ? 'YES' : 'NO';
    ui.tickSeconds.textContent = finite(runtime.tick_seconds) == null ? '—' : `${Number(runtime.tick_seconds).toFixed(2)} s`;
    ui.persistent.textContent = runtime.persistent ? 'YES' : 'NO';
    ui.phase.textContent = text(runtime.phase);

    if (model === 'neurofly-maze-chase-v0.1') drawMaze(state, payload.arena);
    else if (model === 'neurofly-light-chase-v0.1') drawLight(state, payload.arena);
    else drawUnsupported(model);
  }

  async function refresh() {
    try {
      const response = await fetch('/api/platform/state', { cache: 'no-store' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json();
      render(payload);
      ui.connection.textContent = 'LIVE';
      ui.connection.dataset.state = 'live';
    } catch (error) {
      ui.connection.textContent = 'RECONNECTING';
      ui.connection.dataset.state = 'offline';
      ui.runtimeState.textContent = error instanceof Error ? error.message : 'connection failed';
    }
  }

  drawBackground();
  refresh();
  setInterval(refresh, 600);
})();

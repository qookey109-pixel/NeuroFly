(() => {
  const canvas = document.getElementById('mazeCanvas');
  const ctx = canvas.getContext('2d');
  const ui = {
    badge: document.getElementById('brainBadge'),
    status: document.getElementById('runStatus'),
    first: document.getElementById('firstClear'),
    latest: document.getElementById('latestClear'),
    best: document.getElementById('bestClear'),
    clears: document.getElementById('clearCount'),
    history: document.getElementById('clearHistory'),
  };

  const COLS = 19;
  const ROWS = 14;
  const CELL_X = canvas.width / COLS;
  const CELL_Y = canvas.height / ROWS;
  const VALID_ACTIONS = new Set(['TURN_LEFT', 'TURN_RIGHT', 'FORWARD', 'HOLD']);
  const PLAYBACK_MS = 650;
  const REFRESH_MS = 8000;
  const IDLE_ENEMY_MS = 520;

  let activeReceipt = '';
  let playbackTimer = null;
  let idleEnemyTimer = null;
  let currentView = null;
  let currentPayload = null;
  let flashUntil = 0;
  let flashText = '';

  function formatSeconds(value) {
    const seconds = Number(value);
    if (!Number.isFinite(seconds) || seconds < 0) return '—';
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    const minutes = Math.floor(seconds / 60);
    return `${minutes}m ${(seconds % 60).toFixed(1)}s`;
  }

  function neuralStateIsVerified(view) {
    if (!view || view.brain?.backend !== 'malecns') return false;
    if (!VALID_ACTIONS.has(view.last_action)) return false;
    const telemetry = view.brain?.telemetry || {};
    const brainMs = Number(telemetry.brain_ms);
    const spikes = Number(telemetry.total_spikes);
    return Number.isFinite(brainMs) && brainMs > 0 && Number.isFinite(spikes) && spikes > 0;
  }

  function payloadIsVerified(payload) {
    if (!payload || payload.schema !== 'neurofly-malecns-site-state-v1') return false;
    if (payload.verified !== true || payload.backend !== 'malecns') return false;
    if (!/^[a-f0-9]{64}$/i.test(payload.source_receipt_sha256 || '')) return false;
    if (!Array.isArray(payload.trajectory) || payload.trajectory.length < 1) return false;
    return payload.trajectory.every(neuralStateIsVerified);
  }

  function roundedRect(x, y, w, h, r) {
    ctx.beginPath();
    if (typeof ctx.roundRect === 'function') ctx.roundRect(x, y, w, h, r);
    else ctx.rect(x, y, w, h);
  }

  function drawFood(cx, cy, power) {
    ctx.save();
    ctx.beginPath();
    ctx.arc(cx, cy, power ? 8 : 4, 0, Math.PI * 2);
    ctx.fillStyle = power ? '#80d4ff' : '#f6d96b';
    ctx.shadowColor = ctx.fillStyle;
    ctx.shadowBlur = power ? 16 : 7;
    ctx.fill();
    ctx.restore();
  }

  function drawFly(fly) {
    const cx = fly.x * CELL_X + CELL_X / 2;
    const cy = fly.y * CELL_Y + CELL_Y / 2;
    const angle = ({ RIGHT: 0, DOWN: Math.PI / 2, LEFT: Math.PI, UP: -Math.PI / 2 })[fly.dir] || 0;
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(angle);
    ctx.fillStyle = 'rgba(220,255,245,.72)';
    ctx.strokeStyle = 'rgba(143,242,183,.95)';
    ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.ellipse(-4, -13, 13, 7, -.5, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    ctx.beginPath(); ctx.ellipse(-4, 13, 13, 7, .5, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    ctx.fillStyle = '#d8ff73';
    ctx.beginPath(); ctx.ellipse(0, 0, 16, 9, 0, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#17231e';
    for (let x = -7; x <= 7; x += 6) ctx.fillRect(x, -8, 2, 16);
    ctx.fillStyle = '#91d65b';
    ctx.beginPath(); ctx.arc(14, 0, 8, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#ff6674';
    ctx.beginPath(); ctx.arc(17, -4, 3, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.arc(17, 4, 3, 0, Math.PI * 2); ctx.fill();
    ctx.restore();
  }

  function drawEnemy(enemy, index) {
    const cx = enemy.x * CELL_X + CELL_X / 2;
    const cy = enemy.y * CELL_Y + CELL_Y / 2;
    ctx.save();
    ctx.translate(cx, cy);
    ctx.fillStyle = index === 0 ? '#ff6f80' : '#cb79ff';
    ctx.beginPath();
    ctx.arc(0, -3, 14, Math.PI, 0);
    ctx.lineTo(14, 10);
    ctx.quadraticCurveTo(8, 15, 3, 10);
    ctx.quadraticCurveTo(-2, 15, -7, 10);
    ctx.quadraticCurveTo(-11, 14, -14, 10);
    ctx.closePath();
    ctx.fill();
    ctx.fillStyle = '#f8fbfa';
    ctx.beginPath(); ctx.arc(-5, -4, 4, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.arc(5, -4, 4, 0, Math.PI * 2); ctx.fill();
    ctx.restore();
  }

  function drawWaiting(message) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const gradient = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
    gradient.addColorStop(0, '#06100d');
    gradient.addColorStop(1, '#020605');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.textAlign = 'center';
    ctx.fillStyle = '#d8ff73';
    ctx.font = '800 34px system-ui, sans-serif';
    ctx.fillText('MALECNS LOCKED', canvas.width / 2, canvas.height / 2 - 12);
    ctx.fillStyle = '#a8bbb3';
    ctx.font = '16px system-ui, sans-serif';
    ctx.fillText(message, canvas.width / 2, canvas.height / 2 + 26);
  }

  function draw(view) {
    if (!neuralStateIsVerified(view)) {
      drawWaiting('No verified neural decision available.');
      return;
    }

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const gradient = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
    gradient.addColorStop(0, '#06100d');
    gradient.addColorStop(1, '#0b1814');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    const grid = view.grid || [];
    for (let y = 0; y < ROWS; y++) {
      const row = grid[y] || ''.padEnd(COLS, '#');
      for (let x = 0; x < COLS; x++) {
        const cell = row[x];
        const px = x * CELL_X;
        const py = y * CELL_Y;
        if (cell === '#') {
          ctx.fillStyle = '#17392f';
          roundedRect(px + 4, py + 4, CELL_X - 8, CELL_Y - 8, 9);
          ctx.fill();
          ctx.strokeStyle = '#2b5a4a';
          ctx.lineWidth = 1;
          ctx.stroke();
        } else {
          ctx.fillStyle = ((x + y) % 2 === 0) ? '#07120f' : '#081510';
          ctx.fillRect(px, py, CELL_X, CELL_Y);
          if (cell === '.') drawFood(px + CELL_X / 2, py + CELL_Y / 2, false);
          if (cell === 'o') drawFood(px + CELL_X / 2, py + CELL_Y / 2, true);
        }
      }
    }

    (view.enemies || []).forEach(drawEnemy);
    if (view.fly) drawFly(view.fly);

    if (Date.now() < flashUntil && flashText) {
      ctx.fillStyle = 'rgba(0, 0, 0, .58)';
      ctx.fillRect(0, canvas.height / 2 - 42, canvas.width, 84);
      ctx.textAlign = 'center';
      ctx.fillStyle = '#d8ff73';
      ctx.font = '800 30px system-ui, sans-serif';
      ctx.fillText(flashText, canvas.width / 2, canvas.height / 2 + 10);
    }
  }

  function updateGoalHud(payload, view) {
    const finalState = payload.final_state || view || {};
    const history = Array.isArray(finalState.clear_history) ? finalState.clear_history : [];
    ui.first.textContent = formatSeconds(finalState.first_clear_seconds);
    ui.latest.textContent = formatSeconds(finalState.latest_clear_seconds);
    ui.best.textContent = formatSeconds(finalState.best_clear_seconds);
    ui.clears.textContent = String(finalState.total_clears || history.length || 0);

    if (history.length) {
      ui.history.textContent = history.slice(-5).map(item =>
        `#${item.clear_index} ${formatSeconds(item.seconds)} · ${item.ticks} decisions`
      ).join('   ');
    } else {
      ui.history.textContent = 'No clear yet';
    }
  }

  function openNeighbors(view, enemy) {
    const grid = view.grid || [];
    const candidates = [
      { x: enemy.x + 1, y: enemy.y },
      { x: enemy.x - 1, y: enemy.y },
      { x: enemy.x, y: enemy.y + 1 },
      { x: enemy.x, y: enemy.y - 1 },
    ];
    return candidates.filter(({ x, y }) => {
      if (x < 0 || y < 0 || x >= COLS || y >= ROWS) return false;
      if ((grid[y] || '')[x] === '#') return false;
      if (view.fly && view.fly.x === x && view.fly.y === y) return false;
      return true;
    });
  }

  function stopIdleEnemies() {
    clearInterval(idleEnemyTimer);
    idleEnemyTimer = null;
  }

  function startIdleEnemies() {
    stopIdleEnemies();
    if (!currentView || !neuralStateIsVerified(currentView)) return;

    let idleTick = 0;
    idleEnemyTimer = setInterval(() => {
      if (playbackTimer || !currentView) return;
      const enemies = (currentView.enemies || []).map((enemy, index) => {
        const options = openNeighbors(currentView, enemy);
        if (!options.length) return { ...enemy };
        const pick = options[(idleTick + index * 2) % options.length];
        return { ...pick };
      });
      idleTick += 1;
      currentView = { ...currentView, enemies };
      draw(currentView);
      if (currentPayload) updateGoalHud(currentPayload, currentView);
      ui.status.textContent = `MALECNS RESTING · environment active · episode ${currentView.episode}`;
    }, IDLE_ENEMY_MS);
  }

  function playPayload(payload) {
    clearInterval(playbackTimer);
    stopIdleEnemies();
    currentPayload = payload;
    const trajectory = payload.trajectory;
    let index = 0;
    ui.badge.textContent = 'MALECNS · VERIFIED';
    updateGoalHud(payload, trajectory[0]);

    const show = () => {
      const view = trajectory[index];
      currentView = view;
      draw(view);
      updateGoalHud(payload, view);
      ui.status.textContent = `SELF-TRAINING · decision ${index + 1}/${trajectory.length} · episode ${view.episode}`;

      if (view.last_event === 'captured') {
        flashText = 'CAPTURED · RESTART';
        flashUntil = Date.now() + 900;
      } else if (view.last_event === 'maze_cleared') {
        flashText = `CLEAR · ${formatSeconds(view.latest_clear_seconds)}`;
        flashUntil = Date.now() + 1400;
      }

      index += 1;
      if (index >= trajectory.length) {
        clearInterval(playbackTimer);
        playbackTimer = null;
        ui.status.textContent = `MALECNS RESTING · environment active · episode ${view.episode}`;
        startIdleEnemies();
      }
    };

    show();
    if (trajectory.length > 1) playbackTimer = setInterval(show, PLAYBACK_MS);
  }

  async function refresh() {
    try {
      const response = await fetch(`./malecns-state.json?t=${Date.now()}`, { cache: 'no-store' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json();
      if (!payloadIsVerified(payload)) throw new Error('unverified MaleCNS state');
      if (payload.source_receipt_sha256 === activeReceipt) return;
      activeReceipt = payload.source_receipt_sha256;
      playPayload(payload);
    } catch (error) {
      if (!activeReceipt) {
        ui.badge.textContent = 'MALECNS · LOCKED';
        ui.status.textContent = 'Waiting for verified MaleCNS training data';
        drawWaiting('Waiting for verified MaleCNS training data.');
      }
    }
  }

  drawWaiting('Checking verified MaleCNS training data…');
  refresh();
  setInterval(refresh, REFRESH_MS);
})();

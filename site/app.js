(() => {
  const canvas = document.getElementById('mazeCanvas');
  const ctx = canvas.getContext('2d');
  const ui = {
    toggle: document.getElementById('toggleButton'),
    reset: document.getElementById('resetButton'),
    speed: document.getElementById('speedSelect'),
    runtime: document.getElementById('runtimeStatus'),
    score: document.getElementById('scoreValue'),
    episode: document.getElementById('episodeValue'),
    food: document.getElementById('foodValue'),
    survival: document.getElementById('survivalValue'),
    action: document.getElementById('actionValue'),
    lastReward: document.getElementById('lastRewardValue'),
    foodLeft: document.getElementById('foodLeftValue'),
    controller: document.getElementById('controllerValue'),
    modeTag: document.getElementById('modeTag'),
    brainNote: document.getElementById('brainNote'),
    log: document.getElementById('eventLog'),
    visualBar: document.getElementById('visualBar'),
    rewardBar: document.getElementById('rewardBar'),
    threatBar: document.getElementById('threatBar'),
    actionBar: document.getElementById('actionBar'),
  };

  const COLS = 19;
  const ROWS = 14;
  const CELL = canvas.width / COLS;
  const VALID_ACTIONS = new Set(['TURN_LEFT', 'TURN_RIGHT', 'FORWARD', 'HOLD']);
  const requestedApi = new URLSearchParams(window.location.search).get('api');
  const apiBase = requestedApi ? requestedApi.replace(/\/$/, '') : null;

  let mode = 'waiting';
  let running = false;
  let speed = 1;
  let trajectory = [];
  let trajectoryIndex = 0;
  let playbackTimer = null;
  let remoteTimer = null;
  let lastRemoteEventKey = '';
  let sourceReceipt = '';

  function logEvent(message) {
    if (!message) return;
    const li = document.createElement('li');
    li.textContent = message;
    ui.log.prepend(li);
    while (ui.log.children.length > 6) ui.log.removeChild(ui.log.lastChild);
  }

  function setBar(element, value) {
    const level = Math.max(0, Math.min(100, Number(value) || 0));
    element.style.setProperty('--level', `${level}%`);
  }

  function roundedRect(x, y, w, h, r) {
    ctx.beginPath();
    if (typeof ctx.roundRect === 'function') ctx.roundRect(x, y, w, h, r);
    else ctx.rect(x, y, w, h);
  }

  function drawFood(cx, cy, power) {
    ctx.save();
    ctx.beginPath();
    ctx.arc(cx, cy, power ? 6.5 : 3.2, 0, Math.PI * 2);
    ctx.fillStyle = power ? '#80d4ff' : '#f6d96b';
    ctx.shadowColor = ctx.fillStyle;
    ctx.shadowBlur = power ? 13 : 5;
    ctx.fill();
    ctx.restore();
  }

  function drawFly(fly) {
    const cx = fly.x * CELL + CELL / 2;
    const cy = fly.y * CELL + CELL / 2;
    const angle = ({ RIGHT: 0, DOWN: Math.PI / 2, LEFT: Math.PI, UP: -Math.PI / 2 })[fly.dir] || 0;
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(angle);
    ctx.fillStyle = 'rgba(220,255,245,.65)';
    ctx.strokeStyle = 'rgba(143,242,183,.9)';
    ctx.lineWidth = 1;
    ctx.beginPath(); ctx.ellipse(-3, -10, 10, 6, -.5, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    ctx.beginPath(); ctx.ellipse(-3, 10, 10, 6, .5, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    ctx.fillStyle = '#d8ff73';
    ctx.beginPath(); ctx.ellipse(0, 0, 13, 7, 0, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#1b2922';
    for (let x = -5; x <= 6; x += 5) ctx.fillRect(x, -6, 2, 12);
    ctx.fillStyle = '#9bd65c';
    ctx.beginPath(); ctx.arc(11, 0, 6.5, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#ff6d78';
    ctx.beginPath(); ctx.arc(13, -3, 2.2, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.arc(13, 3, 2.2, 0, Math.PI * 2); ctx.fill();
    ctx.restore();
  }

  function drawEnemy(enemy, index, powerTicks) {
    const cx = enemy.x * CELL + CELL / 2;
    const cy = enemy.y * CELL + CELL / 2;
    ctx.save(); ctx.translate(cx, cy);
    ctx.fillStyle = powerTicks > 0 ? '#526e82' : index === 0 ? '#ff7d8c' : '#ce7dff';
    ctx.beginPath(); ctx.arc(0, -2, 11, Math.PI, 0); ctx.lineTo(11, 8);
    ctx.quadraticCurveTo(6, 12, 2, 8); ctx.quadraticCurveTo(-2, 12, -6, 8);
    ctx.quadraticCurveTo(-9, 11, -11, 8); ctx.closePath(); ctx.fill();
    ctx.fillStyle = '#f7fbf9';
    ctx.beginPath(); ctx.arc(-4, -3, 3, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.arc(4, -3, 3, 0, Math.PI * 2); ctx.fill();
    ctx.restore();
  }

  function threatDistance(view) {
    if (!view?.fly || !Array.isArray(view.enemies) || !view.enemies.length) return 99;
    return Math.min(...view.enemies.map(e => Math.abs(e.x - view.fly.x) + Math.abs(e.y - view.fly.y)));
  }

  function neuralStateIsVerified(view) {
    if (!view || view.brain?.backend !== 'malecns') return false;
    if (!VALID_ACTIONS.has(view.last_action)) return false;
    const telemetry = view.brain?.telemetry || {};
    const brainMs = Number(telemetry.brain_ms);
    const spikes = Number(telemetry.total_spikes);
    return Number.isFinite(brainMs) && brainMs > 0 && Number.isFinite(spikes) && spikes > 0;
  }

  function publishedPayloadIsVerified(payload) {
    if (!payload || payload.schema !== 'neurofly-malecns-site-state-v1') return false;
    if (payload.verified !== true || payload.backend !== 'malecns') return false;
    if (!/^[a-f0-9]{64}$/i.test(payload.source_receipt_sha256 || '')) return false;
    if (!Array.isArray(payload.trajectory) || payload.trajectory.length < 1) return false;
    return payload.trajectory.every(neuralStateIsVerified);
  }

  function drawWaiting(message = 'Waiting for verified MaleCNS activity') {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const gradient = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
    gradient.addColorStop(0, '#06100d');
    gradient.addColorStop(1, '#0b1814');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.textAlign = 'center';
    ctx.fillStyle = '#d8ff73';
    ctx.font = '700 26px system-ui, sans-serif';
    ctx.fillText('MALECNS LOCKED', canvas.width / 2, canvas.height / 2 - 18);
    ctx.fillStyle = '#b7c9c1';
    ctx.font = '15px system-ui, sans-serif';
    ctx.fillText(message, canvas.width / 2, canvas.height / 2 + 16);
    ctx.fillText('No demo agent is allowed to move the fly.', canvas.width / 2, canvas.height / 2 + 42);
  }

  function renderMaze(view) {
    if (!neuralStateIsVerified(view)) {
      enterWaiting('Neural telemetry is missing or unverified.');
      return;
    }
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const gradient = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
    gradient.addColorStop(0, '#06100d'); gradient.addColorStop(1, '#0b1814');
    ctx.fillStyle = gradient; ctx.fillRect(0, 0, canvas.width, canvas.height);
    const grid = view.grid || [];
    for (let y = 0; y < ROWS; y++) {
      const row = grid[y] || ''.padEnd(COLS, '#');
      for (let x = 0; x < COLS; x++) {
        const cell = row[x];
        const px = x * CELL, py = y * CELL;
        if (cell === '#') {
          ctx.fillStyle = '#17392f';
          roundedRect(px + 3, py + 3, CELL - 6, CELL - 6, 8);
          ctx.fill(); ctx.strokeStyle = '#2b5a4a'; ctx.lineWidth = 1; ctx.stroke();
        } else {
          ctx.fillStyle = ((x + y) % 2 === 0) ? '#07120f' : '#081510';
          ctx.fillRect(px, py, CELL, CELL);
          if (cell === '.') drawFood(px + CELL / 2, py + CELL / 2, false);
          if (cell === 'o') drawFood(px + CELL / 2, py + CELL / 2, true);
        }
      }
    }
    (view.enemies || []).forEach((enemy, index) => drawEnemy(enemy, index, view.power_ticks || 0));
    if (view.fly) drawFly(view.fly);
    if ((view.power_ticks || 0) > 0) {
      ctx.fillStyle = 'rgba(128, 212, 255, .08)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
    }
    updateUI(view);
  }

  function updateUI(view) {
    const telemetry = view.brain.telemetry || {};
    ui.score.textContent = Number(view.episode_reward || 0).toFixed(1);
    ui.episode.textContent = String(view.episode || 1);
    ui.food.textContent = String(view.episode_food || 0);
    ui.survival.textContent = `${Number(view.survival_seconds || 0).toFixed(0)}s`;
    ui.action.textContent = view.last_action || 'HOLD';
    ui.lastReward.textContent = Number(view.last_reward || 0).toFixed(2);
    ui.foodLeft.textContent = String(view.food_left ?? 0);
    ui.controller.textContent = 'MaleCNS v1.0';
    ui.modeTag.textContent = mode === 'remote' ? 'MALECNS LIVE' : 'MALECNS RECORDED';
    ui.runtime.textContent = `${ui.modeTag.textContent} · ${running ? 'RUNNING' : 'PAUSED'}`;
    ui.toggle.textContent = running ? '暫停' : '繼續';

    const threat = threatDistance(view);
    const totalSpikes = Number(telemetry.total_spikes || 0);
    const rewardSpikes = Number(telemetry.reward_spikes || 0);
    setBar(ui.visualBar, Math.min(100, Math.log10(totalSpikes + 1) * 24));
    setBar(ui.rewardBar, Math.min(100, rewardSpikes / 2));
    setBar(ui.threatBar, Math.max(4, 100 - threat * 15));
    setBar(ui.actionBar, ({ HOLD: 18, FORWARD: 52, TURN_LEFT: 72, TURN_RIGHT: 78 })[view.last_action] || 30);

    const receiptText = sourceReceipt ? ` · receipt ${sourceReceipt.slice(0, 10)}…` : '';
    ui.brainNote.textContent = `Verified MaleCNS：${totalSpikes.toLocaleString()} spikes；神經時間 ${Number(telemetry.brain_ms || 0).toFixed(0)} ms${receiptText}`;
  }

  function enterWaiting(message) {
    mode = 'waiting';
    running = false;
    clearInterval(playbackTimer);
    playbackTimer = null;
    ui.runtime.textContent = 'Waiting for MaleCNS · LOCKED';
    ui.controller.textContent = 'Locked — no demo agent';
    ui.modeTag.textContent = 'WAITING MALECNS';
    ui.toggle.textContent = '等待真腦';
    ui.toggle.disabled = true;
    ui.reset.disabled = true;
    ui.speed.disabled = true;
    ui.score.textContent = '—';
    ui.episode.textContent = '—';
    ui.food.textContent = '—';
    ui.survival.textContent = '—';
    ui.action.textContent = 'LOCKED';
    ui.lastReward.textContent = '—';
    ui.foodLeft.textContent = '—';
    ui.brainNote.textContent = message;
    setBar(ui.visualBar, 0); setBar(ui.rewardBar, 0); setBar(ui.threatBar, 0); setBar(ui.actionBar, 0);
    drawWaiting(message);
  }

  function unlockControls() {
    ui.toggle.disabled = false;
    ui.reset.disabled = false;
    ui.speed.disabled = false;
  }

  function schedulePlayback() {
    clearInterval(playbackTimer);
    if (mode !== 'recorded' || !running || trajectory.length === 0) return;
    playbackTimer = setInterval(() => {
      const view = trajectory[trajectoryIndex];
      if (!neuralStateIsVerified(view)) {
        enterWaiting('A recorded state failed neural verification.');
        return;
      }
      renderMaze(view);
      const event = view.last_event;
      if (event) logEvent(`MaleCNS：${event} · reward ${Number(view.last_reward || 0).toFixed(2)}`);
      trajectoryIndex = (trajectoryIndex + 1) % trajectory.length;
    }, Math.max(250, 1100 / speed));
  }

  async function fetchJson(url, options = {}) {
    const response = await fetch(url, { cache: 'no-store', ...options });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }

  async function tryRemoteMaleCNS() {
    if (!apiBase) return false;
    try {
      const status = await fetchJson(`${apiBase}/api/status`);
      if (status.backend !== 'malecns' || status.running !== true) return false;
      const state = await fetchJson(`${apiBase}/api/state`);
      if (!neuralStateIsVerified(state)) return false;
      mode = 'remote'; running = true; sourceReceipt = '';
      unlockControls();
      renderMaze(state);
      logEvent('已連接 verified MaleCNS backend');
      clearInterval(remoteTimer);
      remoteTimer = setInterval(async () => {
        if (!running) return;
        try {
          const next = await fetchJson(`${apiBase}/api/state`);
          if (!neuralStateIsVerified(next)) {
            enterWaiting('MaleCNS backend stopped providing verified neural decisions.');
            return;
          }
          const eventKey = `${next.episode}:${next.last_event || ''}:${next.ticks}`;
          if (next.last_event && eventKey !== lastRemoteEventKey) {
            logEvent(`MaleCNS：${next.last_event} · reward ${Number(next.last_reward || 0).toFixed(2)}`);
            lastRemoteEventKey = eventKey;
          }
          renderMaze(next);
        } catch (error) {
          enterWaiting(`MaleCNS backend disconnected: ${error.message}`);
        }
      }, 700);
      return true;
    } catch (_) {
      return false;
    }
  }

  async function tryPublishedMaleCNS() {
    try {
      const payload = await fetchJson(`./malecns-state.json?t=${Date.now()}`);
      if (!publishedPayloadIsVerified(payload)) return false;
      trajectory = payload.trajectory;
      trajectoryIndex = 0;
      sourceReceipt = payload.source_receipt_sha256;
      mode = 'recorded'; running = true;
      unlockControls();
      logEvent(`載入 verified MaleCNS trajectory · ${trajectory.length} decision(s)`);
      renderMaze(trajectory[0]);
      trajectoryIndex = trajectory.length > 1 ? 1 : 0;
      schedulePlayback();
      return true;
    } catch (_) {
      return false;
    }
  }

  async function detectVerifiedBrain() {
    enterWaiting('正在等待第一份通過驗證的 MaleCNS 神經決策。');
    if (await tryRemoteMaleCNS()) return;
    if (await tryPublishedMaleCNS()) return;
    setTimeout(detectVerifiedBrain, 15000);
  }

  ui.toggle.addEventListener('click', () => {
    if (mode === 'waiting') return;
    running = !running;
    ui.toggle.textContent = running ? '暫停' : '繼續';
    if (mode === 'recorded') schedulePlayback();
    if (!running) ui.runtime.textContent = `${mode === 'remote' ? 'MALECNS LIVE' : 'MALECNS RECORDED'} · PAUSED`;
  });

  ui.reset.addEventListener('click', () => {
    if (mode !== 'recorded' || trajectory.length === 0) return;
    trajectoryIndex = 0;
    renderMaze(trajectory[0]);
    trajectoryIndex = trajectory.length > 1 ? 1 : 0;
    logEvent('重新播放 verified MaleCNS trajectory');
  });

  ui.speed.addEventListener('change', () => {
    speed = Number(ui.speed.value) || 1;
    if (mode === 'recorded') schedulePlayback();
  });

  detectVerifiedBrain();
})();

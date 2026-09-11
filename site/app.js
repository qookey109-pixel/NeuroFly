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
  const ABS_DIRS = [
    { name: 'UP', x: 0, y: -1 },
    { name: 'RIGHT', x: 1, y: 0 },
    { name: 'DOWN', x: 0, y: 1 },
    { name: 'LEFT', x: -1, y: 0 },
  ];

  let mode = 'detect';
  let running = true;
  let speed = 1;
  let timer = null;
  let pollTimer = null;
  let localState = null;
  let localEpisode = 1;
  let remoteState = null;
  let lastRemoteEventKey = '';

  const requestedApi = new URLSearchParams(window.location.search).get('api');
  const apiBase = (requestedApi || window.location.origin).replace(/\/$/, '');

  function logEvent(message) {
    if (!message) return;
    const li = document.createElement('li');
    li.textContent = message;
    ui.log.prepend(li);
    while (ui.log.children.length > 6) ui.log.removeChild(ui.log.lastChild);
  }

  function makeGrid() {
    const grid = Array.from({ length: ROWS }, () => Array(COLS).fill('.'));
    for (let x = 0; x < COLS; x++) {
      grid[0][x] = '#'; grid[ROWS - 1][x] = '#';
    }
    for (let y = 0; y < ROWS; y++) {
      grid[y][0] = '#'; grid[y][COLS - 1] = '#';
    }
    const wall = (x, y) => { if (x > 0 && x < COLS - 1 && y > 0 && y < ROWS - 1) grid[y][x] = '#'; };
    for (let y = 2; y <= 10; y++) if (![5, 8].includes(y)) wall(4, y);
    for (let y = 3; y <= 11; y++) if (![6, 9].includes(y)) wall(9, y);
    for (let y = 2; y <= 10; y++) if (![4, 7].includes(y)) wall(14, y);
    for (let x = 2; x <= 7; x++) if (x !== 5) wall(x, 3);
    for (let x = 11; x <= 16; x++) if (x !== 13) wall(x, 4);
    for (let x = 2; x <= 7; x++) if (x !== 6) wall(x, 8);
    for (let x = 11; x <= 16; x++) if (x !== 12) wall(x, 9);
    for (let x = 6; x <= 12; x++) if (![8, 10].includes(x)) wall(x, 11);
    return grid;
  }

  function resetLocal(reason = 'Demo episode reset') {
    const grid = makeGrid();
    const fly = { x: 1, y: 1, dir: 'RIGHT' };
    const enemies = [
      { x: COLS - 2, y: ROWS - 2, phase: 0 },
      { x: COLS - 3, y: 1, phase: Math.PI },
    ];
    grid[fly.y][fly.x] = ' ';
    enemies.forEach(e => { grid[e.y][e.x] = ' '; });
    [[1, ROWS - 2], [COLS - 2, 1], [8, 6], [15, 11]].forEach(([x, y]) => {
      if (grid[y][x] !== '#') grid[y][x] = 'o';
    });
    localState = {
      grid, fly, enemies,
      reward: 0, lastReward: 0, foodEaten: 0,
      powerTicks: 0, ticks: 0, lastAction: 'HOLD',
      startedAt: performance.now(),
    };
    logEvent(reason);
    renderCurrent();
  }

  function isOpen(grid, x, y) {
    return y >= 0 && y < ROWS && x >= 0 && x < COLS && grid[y][x] !== '#';
  }

  function neighbors(grid, pos) {
    return ABS_DIRS
      .map(d => ({ ...d, x: pos.x + d.x, y: pos.y + d.y }))
      .filter(p => isOpen(grid, p.x, p.y));
  }

  function nearestFoodDistance(grid, start) {
    const queue = [{ x: start.x, y: start.y, d: 0 }];
    const seen = new Set([`${start.x},${start.y}`]);
    for (let i = 0; i < queue.length; i++) {
      const p = queue[i];
      if (grid[p.y][p.x] === '.' || grid[p.y][p.x] === 'o') return p.d;
      for (const n of neighbors(grid, p)) {
        const key = `${n.x},${n.y}`;
        if (!seen.has(key)) {
          seen.add(key); queue.push({ x: n.x, y: n.y, d: p.d + 1 });
        }
      }
    }
    return 999;
  }

  function countLocalFood() {
    return localState.grid.flat().filter(cell => cell === '.' || cell === 'o').length;
  }

  function localThreat(pos) {
    return Math.min(...localState.enemies.map(e => Math.abs(e.x - pos.x) + Math.abs(e.y - pos.y)));
  }

  function chooseLocalAction() {
    const options = neighbors(localState.grid, localState.fly);
    if (!options.length) return null;
    let best = options[0];
    let score = Infinity;
    for (const option of options) {
      const food = nearestFoodDistance(localState.grid, option);
      const threat = localThreat(option);
      const danger = localState.powerTicks > 0 ? 0 : threat <= 1 ? 30 : threat === 2 ? 7 : 0;
      const candidate = food + danger + Math.random() * 1.1;
      if (candidate < score) { score = candidate; best = option; }
    }
    return best;
  }

  function moveLocalEnemies() {
    for (const enemy of localState.enemies) {
      const options = neighbors(localState.grid, enemy);
      if (!options.length) continue;
      options.sort((a, b) => {
        const da = Math.abs(a.x - localState.fly.x) + Math.abs(a.y - localState.fly.y);
        const db = Math.abs(b.x - localState.fly.x) + Math.abs(b.y - localState.fly.y);
        return localState.powerTicks > 0 ? db - da : da - db;
      });
      const pick = Math.random() < 0.72 ? options[0] : options[Math.floor(Math.random() * options.length)];
      enemy.x = pick.x; enemy.y = pick.y; enemy.phase += 0.35;
    }
  }

  function localTick() {
    if (!running || mode !== 'demo') return;
    localState.ticks++;
    localState.lastReward = 0.01;
    localState.reward += 0.01;
    const action = chooseLocalAction();
    if (action) {
      localState.fly.x = action.x; localState.fly.y = action.y;
      localState.fly.dir = action.name; localState.lastAction = action.name;
    }
    const cell = localState.grid[localState.fly.y][localState.fly.x];
    if (cell === '.') {
      localState.grid[localState.fly.y][localState.fly.x] = ' ';
      localState.foodEaten++; localState.lastReward += 1; localState.reward += 1;
    } else if (cell === 'o') {
      localState.grid[localState.fly.y][localState.fly.x] = ' ';
      localState.foodEaten++; localState.powerTicks = 34;
      localState.lastReward += 4; localState.reward += 4;
      logEvent('Demo：吃到能量食物 · +4');
    }
    moveLocalEnemies();
    const hit = localState.enemies.find(e => e.x === localState.fly.x && e.y === localState.fly.y);
    if (hit) {
      if (localState.powerTicks > 0) {
        localState.reward += 3; localState.lastReward += 3;
        hit.x = COLS - 2; hit.y = ROWS - 2;
        logEvent('Demo：驅離敵人 · +3');
      } else {
        localState.reward -= 5; localState.lastReward -= 5;
        localEpisode++;
        resetLocal('Demo：被捕捉，開始新 episode');
        return;
      }
    }
    if (localState.powerTicks > 0) localState.powerTicks--;
    if (countLocalFood() === 0) {
      localEpisode++;
      resetLocal('Demo：迷宮清空 · +15');
      return;
    }
    renderCurrent();
  }

  function localSnapshot() {
    return {
      grid: localState.grid.map(row => row.join('')),
      fly: localState.fly,
      enemies: localState.enemies,
      power_ticks: localState.powerTicks,
      episode: localEpisode,
      episode_reward: localState.reward,
      episode_food: localState.foodEaten,
      food_left: countLocalFood(),
      survival_seconds: (performance.now() - localState.startedAt) / 1000,
      last_action: localState.lastAction,
      last_reward: localState.lastReward,
      last_event: null,
      brain: { backend: 'demo', telemetry: {} },
      runtime: { running },
    };
  }

  function threatDistance(view) {
    return Math.min(...view.enemies.map(e => Math.abs(e.x - view.fly.x) + Math.abs(e.y - view.fly.y)));
  }

  function setBar(element, value) {
    const level = Math.max(0, Math.min(100, Number(value) || 0));
    element.style.setProperty('--level', `${level}%`);
  }

  function updateUI(view) {
    const backend = view.brain?.backend || 'demo';
    const telemetry = view.brain?.telemetry || {};
    ui.score.textContent = Number(view.episode_reward || 0).toFixed(1);
    ui.episode.textContent = String(view.episode || 1);
    ui.food.textContent = String(view.episode_food || 0);
    ui.survival.textContent = `${Number(view.survival_seconds || 0).toFixed(0)}s`;
    ui.action.textContent = view.last_action || 'HOLD';
    ui.lastReward.textContent = Number(view.last_reward || 0).toFixed(2);
    ui.foodLeft.textContent = String(view.food_left ?? 0);
    ui.controller.textContent = backend === 'malecns' ? 'MaleCNS v1.0' : 'Demo heuristic';
    ui.modeTag.textContent = backend === 'malecns' ? 'MALECNS' : 'DEMO';

    const runningNow = view.runtime?.running ?? running;
    ui.runtime.textContent = `${backend === 'malecns' ? 'MaleCNS' : 'Demo Agent'} · ${runningNow ? 'RUNNING' : 'PAUSED'}`;
    ui.toggle.textContent = runningNow ? '暫停' : '繼續';

    const threat = threatDistance(view);
    const totalSpikes = Number(telemetry.total_spikes || 0);
    const rewardSpikes = Number(telemetry.reward_spikes || 0);
    setBar(ui.visualBar, backend === 'malecns' ? Math.min(100, Math.log10(totalSpikes + 1) * 24) : 62);
    setBar(ui.rewardBar, backend === 'malecns' ? Math.min(100, rewardSpikes / 2) : Math.max(0, Number(view.last_reward || 0) * 14));
    setBar(ui.threatBar, Math.max(4, 100 - threat * 15));
    setBar(ui.actionBar, ({ HOLD: 18, FORWARD: 52, UP: 52, DOWN: 58, LEFT: 72, RIGHT: 78, TURN_LEFT: 72, TURN_RIGHT: 78 })[view.last_action] || 30);

    if (backend === 'malecns') {
      ui.brainNote.textContent = `真實 MaleCNS runtime：${Number(telemetry.total_spikes || 0).toLocaleString()} spikes / decision；神經時間 ${Number(telemetry.brain_ms || 0).toFixed(0)} ms。`;
    } else {
      ui.brainNote.textContent = mode === 'remote'
        ? '已連接 persistent backend，但目前後端使用 Demo Brain；可在 server 啟動時改成 --brain malecns。'
        : '目前是瀏覽器 Demo Agent。啟動 NeuroFly maze-server 後，網站會切換成 persistent backend。';
    }
  }

  function draw(view) {
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
      ctx.fillStyle = 'rgba(128, 212, 255, .08)'; ctx.fillRect(0, 0, canvas.width, canvas.height);
    }
  }

  function roundedRect(x, y, w, h, r) {
    ctx.beginPath();
    if (typeof ctx.roundRect === 'function') ctx.roundRect(x, y, w, h, r);
    else ctx.rect(x, y, w, h);
  }

  function drawFood(cx, cy, power) {
    ctx.save(); ctx.beginPath(); ctx.arc(cx, cy, power ? 6.5 : 3.2, 0, Math.PI * 2);
    ctx.fillStyle = power ? '#80d4ff' : '#f6d96b'; ctx.shadowColor = ctx.fillStyle;
    ctx.shadowBlur = power ? 13 : 5; ctx.fill(); ctx.restore();
  }

  function drawFly(fly) {
    const cx = fly.x * CELL + CELL / 2, cy = fly.y * CELL + CELL / 2;
    const angle = ({ RIGHT: 0, DOWN: Math.PI / 2, LEFT: Math.PI, UP: -Math.PI / 2 })[fly.dir] || 0;
    ctx.save(); ctx.translate(cx, cy); ctx.rotate(angle);
    ctx.fillStyle = 'rgba(220,255,245,.65)'; ctx.strokeStyle = 'rgba(143,242,183,.9)'; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.ellipse(-3, -10, 10, 6, -.5, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    ctx.beginPath(); ctx.ellipse(-3, 10, 10, 6, .5, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    ctx.fillStyle = '#d8ff73'; ctx.beginPath(); ctx.ellipse(0, 0, 13, 7, 0, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#1b2922'; for (let x = -5; x <= 6; x += 5) ctx.fillRect(x, -6, 2, 12);
    ctx.fillStyle = '#9bd65c'; ctx.beginPath(); ctx.arc(11, 0, 6.5, 0, 0 + Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#ff6d78'; ctx.beginPath(); ctx.arc(13, -3, 2.2, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.arc(13, 3, 2.2, 0, Math.PI * 2); ctx.fill();
    ctx.restore();
  }

  function drawEnemy(enemy, index, powerTicks) {
    const cx = enemy.x * CELL + CELL / 2, cy = enemy.y * CELL + CELL / 2;
    ctx.save(); ctx.translate(cx, cy);
    ctx.fillStyle = powerTicks > 0 ? '#526e82' : index === 0 ? '#ff7d8c' : '#ce7dff';
    ctx.beginPath(); ctx.arc(0, -2, 11, Math.PI, 0); ctx.lineTo(11, 8);
    ctx.quadraticCurveTo(6, 12, 2, 8); ctx.quadraticCurveTo(-2, 12, -6, 8);
    ctx.quadraticCurveTo(-9, 11, -11, 8); ctx.closePath(); ctx.fill();
    ctx.fillStyle = '#f7fbf9'; ctx.beginPath(); ctx.arc(-4, -3, 3, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.arc(4, -3, 3, 0, Math.PI * 2); ctx.fill(); ctx.restore();
  }

  function renderCurrent() {
    const view = mode === 'remote' ? remoteState : localSnapshot();
    if (!view) return;
    draw(view); updateUI(view);
  }

  async function apiFetch(path, options = {}) {
    const response = await fetch(`${apiBase}${path}`, { cache: 'no-store', ...options });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }

  async function pollRemote() {
    try {
      remoteState = await apiFetch('/api/state');
      const eventKey = `${remoteState.episode}:${remoteState.last_event || ''}:${remoteState.ticks}`;
      if (remoteState.last_event && eventKey !== lastRemoteEventKey) {
        logEvent(`Backend：${remoteState.last_event} · reward ${Number(remoteState.last_reward || 0).toFixed(2)}`);
        lastRemoteEventKey = eventKey;
      }
      renderCurrent();
    } catch (error) {
      ui.runtime.textContent = 'Backend disconnected';
      ui.brainNote.textContent = `Persistent backend 暫時無法讀取：${error.message}`;
    }
  }

  async function controlRemote(payload) {
    remoteState = await apiFetch('/api/control', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
    });
    renderCurrent();
  }

  function scheduleLocal() {
    clearInterval(timer);
    timer = setInterval(localTick, Math.max(70, 360 / speed));
  }

  function startDemo() {
    mode = 'demo'; running = true;
    ui.modeTag.textContent = 'DEMO';
    ui.runtime.textContent = 'Demo Agent · RUNNING';
    ui.controller.textContent = 'Demo heuristic';
    resetLocal('Demo Agent 啟動（未連接 persistent backend）');
    scheduleLocal();
  }

  async function startRemote() {
    mode = 'remote';
    clearInterval(timer);
    const status = await apiFetch('/api/status');
    ui.runtime.textContent = `${status.backend === 'malecns' ? 'MaleCNS' : 'Demo Agent'} · ${status.running ? 'RUNNING' : 'PAUSED'}`;
    logEvent(`連接 persistent backend · ${status.backend}`);
    await pollRemote();
    clearInterval(pollTimer);
    pollTimer = setInterval(pollRemote, 650);
  }

  async function detectRuntime() {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 1200);
    try {
      const response = await fetch(`${apiBase}/api/status`, { cache: 'no-store', signal: controller.signal });
      clearTimeout(timeout);
      if (!response.ok) throw new Error('No NeuroFly API');
      const status = await response.json();
      if (!status.ok) throw new Error('Invalid NeuroFly API');
      await startRemote();
    } catch (_) {
      clearTimeout(timeout);
      startDemo();
    }
  }

  ui.toggle.addEventListener('click', async () => {
    if (mode === 'remote') {
      try { await controlRemote({ running: !(remoteState?.runtime?.running ?? true) }); }
      catch (error) { logEvent(`控制失敗：${error.message}`); }
      return;
    }
    running = !running; renderCurrent();
  });

  ui.reset.addEventListener('click', async () => {
    if (mode === 'remote') {
      try { await controlRemote({ reset: true }); logEvent('Backend episode 手動重置'); }
      catch (error) { logEvent(`重置失敗：${error.message}`); }
      return;
    }
    localEpisode++; resetLocal('Demo 手動重置');
  });

  ui.speed.addEventListener('change', async () => {
    speed = Number(ui.speed.value) || 1;
    if (mode === 'remote') {
      try { await controlRemote({ tick_seconds: 0.6 / speed }); }
      catch (error) { logEvent(`速度設定失敗：${error.message}`); }
    } else scheduleLocal();
  });

  detectRuntime();
})();

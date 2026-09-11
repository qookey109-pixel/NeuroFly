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
    log: document.getElementById('eventLog'),
    visualBar: document.getElementById('visualBar'),
    rewardBar: document.getElementById('rewardBar'),
    threatBar: document.getElementById('threatBar'),
    actionBar: document.getElementById('actionBar'),
  };

  const COLS = 19;
  const ROWS = 14;
  const CELL = canvas.width / COLS;
  const DIRS = [
    { name: 'UP', x: 0, y: -1 },
    { name: 'RIGHT', x: 1, y: 0 },
    { name: 'DOWN', x: 0, y: 1 },
    { name: 'LEFT', x: -1, y: 0 },
  ];

  let running = true;
  let speed = 1;
  let timer = null;
  let episode = 1;
  let totalFood = 0;
  let state;

  function makeGrid() {
    const grid = Array.from({ length: ROWS }, () => Array(COLS).fill('.'));
    for (let x = 0; x < COLS; x++) {
      grid[0][x] = '#';
      grid[ROWS - 1][x] = '#';
    }
    for (let y = 0; y < ROWS; y++) {
      grid[y][0] = '#';
      grid[y][COLS - 1] = '#';
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

  function resetEpisode(reason = 'Experiment reset') {
    const grid = makeGrid();
    const fly = { x: 1, y: 1, dir: 'RIGHT' };
    const enemies = [
      { x: COLS - 2, y: ROWS - 2, phase: 0 },
      { x: COLS - 3, y: 1, phase: Math.PI },
    ];

    // Keep spawn cells empty and add four energy-food locations.
    grid[fly.y][fly.x] = ' ';
    enemies.forEach(e => { grid[e.y][e.x] = ' '; });
    [[1, ROWS - 2], [COLS - 2, 1], [8, 6], [15, 11]].forEach(([x, y]) => {
      if (grid[y][x] !== '#') grid[y][x] = 'o';
    });

    state = {
      grid,
      fly,
      enemies,
      reward: 0,
      lastReward: 0,
      foodEaten: 0,
      startedAt: performance.now(),
      ticks: 0,
      powerTicks: 0,
      lastAction: 'HOLD',
    };
    totalFood = countFood();
    logEvent(reason);
    draw();
    updateUI();
  }

  function countFood() {
    let n = 0;
    for (const row of state.grid) for (const cell of row) if (cell === '.' || cell === 'o') n++;
    return n;
  }

  function isOpen(x, y) {
    return y >= 0 && y < ROWS && x >= 0 && x < COLS && state.grid[y][x] !== '#';
  }

  function neighbors(pos) {
    return DIRS.map(d => ({ ...d, x: pos.x + d.x, y: pos.y + d.y })).filter(p => isOpen(p.x, p.y));
  }

  function key(x, y) { return `${x},${y}`; }

  function distanceToNearestFood(start) {
    const queue = [{ x: start.x, y: start.y, d: 0 }];
    const seen = new Set([key(start.x, start.y)]);
    for (let i = 0; i < queue.length; i++) {
      const p = queue[i];
      if (state.grid[p.y][p.x] === '.' || state.grid[p.y][p.x] === 'o') return p.d;
      for (const n of neighbors(p)) {
        const k = key(n.x, n.y);
        if (!seen.has(k)) {
          seen.add(k);
          queue.push({ x: n.x, y: n.y, d: p.d + 1 });
        }
      }
    }
    return 999;
  }

  function threatDistance(pos) {
    return Math.min(...state.enemies.map(e => Math.abs(e.x - pos.x) + Math.abs(e.y - pos.y)));
  }

  function chooseDemoAction() {
    const options = neighbors(state.fly);
    if (!options.length) return null;
    let best = options[0];
    let bestScore = Infinity;
    for (const option of options) {
      const foodDist = distanceToNearestFood(option);
      const threat = threatDistance(option);
      const dangerPenalty = state.powerTicks > 0 ? 0 : threat <= 1 ? 20 : threat === 2 ? 5 : 0;
      const revisitNoise = Math.random() * 1.15;
      const score = foodDist + dangerPenalty + revisitNoise;
      if (score < bestScore) {
        bestScore = score;
        best = option;
      }
    }
    return best;
  }

  function moveEnemies() {
    for (const enemy of state.enemies) {
      const options = neighbors(enemy);
      if (!options.length) continue;
      options.sort((a, b) => {
        const da = Math.abs(a.x - state.fly.x) + Math.abs(a.y - state.fly.y);
        const db = Math.abs(b.x - state.fly.x) + Math.abs(b.y - state.fly.y);
        return state.powerTicks > 0 ? db - da : da - db;
      });
      const chase = Math.random() < 0.72;
      const pick = chase ? options[0] : options[Math.floor(Math.random() * options.length)];
      enemy.x = pick.x;
      enemy.y = pick.y;
      enemy.phase += 0.35;
    }
  }

  function collideEnemy() {
    return state.enemies.find(e => e.x === state.fly.x && e.y === state.fly.y);
  }

  function tick() {
    if (!running) return;
    state.ticks++;
    state.lastReward = 0.01;
    state.reward += state.lastReward;

    const action = chooseDemoAction();
    if (action) {
      state.fly.x = action.x;
      state.fly.y = action.y;
      state.fly.dir = action.name;
      state.lastAction = action.name;
    } else {
      state.lastAction = 'HOLD';
    }

    const cell = state.grid[state.fly.y][state.fly.x];
    if (cell === '.') {
      state.grid[state.fly.y][state.fly.x] = ' ';
      state.foodEaten++;
      state.lastReward += 1;
      state.reward += 1;
      if (state.foodEaten % 8 === 0) logEvent(`找到第 ${state.foodEaten} 顆食物 · +1 reward`);
    } else if (cell === 'o') {
      state.grid[state.fly.y][state.fly.x] = ' ';
      state.foodEaten++;
      state.powerTicks = 34;
      state.lastReward += 4;
      state.reward += 4;
      logEvent('吃到能量食物 · +4 reward · 敵人暫時迴避');
    }

    moveEnemies();

    const hit = collideEnemy();
    if (hit) {
      if (state.powerTicks > 0) {
        state.lastReward += 3;
        state.reward += 3;
        hit.x = COLS - 2;
        hit.y = ROWS - 2;
        logEvent('成功驅離敵人 · +3 reward');
      } else {
        state.lastReward -= 5;
        state.reward -= 5;
        logEvent('被敵人捕捉 · -5 reward');
        episode++;
        resetEpisode('新 episode 開始');
        return;
      }
    }

    if (state.powerTicks > 0) state.powerTicks--;

    if (countFood() === 0) {
      state.lastReward += 15;
      state.reward += 15;
      logEvent('迷宮清空 · +15 reward');
      episode++;
      resetEpisode('完成迷宮，進入下一個 episode');
      return;
    }

    draw();
    updateUI();
  }

  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const g = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
    g.addColorStop(0, '#06100d');
    g.addColorStop(1, '#0b1814');
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    for (let y = 0; y < ROWS; y++) {
      for (let x = 0; x < COLS; x++) {
        const cell = state.grid[y][x];
        const px = x * CELL;
        const py = y * CELL;
        if (cell === '#') {
          ctx.fillStyle = '#17392f';
          roundRect(px + 3, py + 3, CELL - 6, CELL - 6, 8);
          ctx.fill();
          ctx.strokeStyle = '#2b5a4a';
          ctx.lineWidth = 1;
          ctx.stroke();
        } else {
          ctx.fillStyle = ((x + y) % 2 === 0) ? '#07120f' : '#081510';
          ctx.fillRect(px, py, CELL, CELL);
          if (cell === '.') drawFood(px + CELL / 2, py + CELL / 2, false);
          if (cell === 'o') drawFood(px + CELL / 2, py + CELL / 2, true);
        }
      }
    }

    state.enemies.forEach((enemy, i) => drawEnemy(enemy, i));
    drawFly(state.fly);

    if (state.powerTicks > 0) {
      ctx.fillStyle = 'rgba(128, 212, 255, .08)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
    }
  }

  function roundRect(x, y, w, h, r) {
    ctx.beginPath();
    ctx.roundRect(x, y, w, h, r);
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

    // Wings
    ctx.fillStyle = 'rgba(220, 255, 245, .65)';
    ctx.strokeStyle = 'rgba(143, 242, 183, .9)';
    ctx.lineWidth = 1;
    ctx.beginPath(); ctx.ellipse(-3, -10, 10, 6, -.5, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    ctx.beginPath(); ctx.ellipse(-3, 10, 10, 6, .5, 0, Math.PI * 2); ctx.fill(); ctx.stroke();

    // Body
    ctx.fillStyle = '#d8ff73';
    ctx.beginPath(); ctx.ellipse(0, 0, 13, 7, 0, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#1b2922';
    for (let x = -5; x <= 6; x += 5) ctx.fillRect(x, -6, 2, 12);

    // Head and eyes
    ctx.fillStyle = '#9bd65c';
    ctx.beginPath(); ctx.arc(11, 0, 6.5, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#ff6d78';
    ctx.beginPath(); ctx.arc(13, -3, 2.2, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.arc(13, 3, 2.2, 0, Math.PI * 2); ctx.fill();

    // Legs
    ctx.strokeStyle = '#bfe96a';
    ctx.lineWidth = 1.6;
    [[-4,-5,-10,-12], [2,-5,4,-13], [-4,5,-10,12], [2,5,4,13]].forEach(l => {
      ctx.beginPath(); ctx.moveTo(l[0], l[1]); ctx.lineTo(l[2], l[3]); ctx.stroke();
    });
    ctx.restore();
  }

  function drawEnemy(enemy, index) {
    const cx = enemy.x * CELL + CELL / 2;
    const cy = enemy.y * CELL + CELL / 2;
    const pulse = 1 + Math.sin(enemy.phase) * .06;
    ctx.save();
    ctx.translate(cx, cy);
    ctx.scale(pulse, pulse);
    ctx.fillStyle = state.powerTicks > 0 ? '#526e82' : index === 0 ? '#ff7d8c' : '#ce7dff';
    ctx.beginPath();
    ctx.arc(0, -2, 11, Math.PI, 0);
    ctx.lineTo(11, 8);
    ctx.quadraticCurveTo(6, 12, 2, 8);
    ctx.quadraticCurveTo(-2, 12, -6, 8);
    ctx.quadraticCurveTo(-9, 11, -11, 8);
    ctx.closePath();
    ctx.fill();
    ctx.fillStyle = '#f7fbf9';
    ctx.beginPath(); ctx.arc(-4, -3, 3, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.arc(4, -3, 3, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#13201c';
    ctx.beginPath(); ctx.arc(-3, -2, 1.4, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.arc(5, -2, 1.4, 0, Math.PI * 2); ctx.fill();
    ctx.restore();
  }

  function updateUI() {
    const foodLeft = countFood();
    const elapsed = Math.max(0, (performance.now() - state.startedAt) / 1000);
    const threat = Math.max(0, 100 - Math.min(100, threatDistance(state.fly) * 18));
    const rewardSignal = Math.min(100, Math.abs(state.lastReward) * 18 + (state.powerTicks > 0 ? 35 : 0));
    const visualSignal = 45 + Math.min(45, neighbors(state.fly).length * 10);
    const actionSignal = state.lastAction === 'HOLD' ? 15 : 62 + (state.ticks % 3) * 9;

    ui.score.textContent = state.reward.toFixed(1);
    ui.episode.textContent = String(episode);
    ui.food.textContent = String(state.foodEaten);
    ui.survival.textContent = `${Math.floor(elapsed)}s`;
    ui.action.textContent = state.lastAction;
    ui.lastReward.textContent = (state.lastReward >= 0 ? '+' : '') + state.lastReward.toFixed(2);
    ui.foodLeft.textContent = String(foodLeft);
    ui.visualBar.style.setProperty('--level', `${visualSignal}%`);
    ui.rewardBar.style.setProperty('--level', `${rewardSignal}%`);
    ui.threatBar.style.setProperty('--level', `${threat}%`);
    ui.actionBar.style.setProperty('--level', `${Math.min(100, actionSignal)}%`);
  }

  function logEvent(message) {
    const li = document.createElement('li');
    const now = new Date();
    li.innerHTML = `<time>${now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</time>${message}`;
    ui.log.prepend(li);
    while (ui.log.children.length > 8) ui.log.lastElementChild.remove();
  }

  function schedule() {
    if (timer) clearInterval(timer);
    timer = setInterval(tick, Math.max(45, 190 / speed));
  }

  ui.toggle.addEventListener('click', () => {
    running = !running;
    ui.toggle.textContent = running ? '暫停' : '繼續';
    ui.runtime.textContent = `Demo Agent · ${running ? 'RUNNING' : 'PAUSED'}`;
    logEvent(running ? '模擬繼續' : '模擬暫停');
  });

  ui.reset.addEventListener('click', () => {
    episode++;
    resetEpisode('手動重置 experiment');
  });

  ui.speed.addEventListener('change', () => {
    speed = Number(ui.speed.value) || 1;
    schedule();
    logEvent(`模擬速度切換為 ${speed}×`);
  });

  resetEpisode('Maze Chase visualizer 啟動');
  schedule();
})();

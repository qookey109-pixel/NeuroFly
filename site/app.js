(() => {
  const byId = id => document.getElementById(id);
  const canvas = byId('mazeCanvas');
  const ctx = canvas.getContext('2d');

  const ui = {
    badge: byId('brainBadge'),
    connection: byId('connectionState'),
    status: byId('runStatus'),
    reconnectLive: byId('reconnectLive'),
    total: byId('totalTime'),
    first: byId('firstClear'),
    latest: byId('latestClear'),
    best: byId('bestClear'),
    clears: byId('clearCount'),
    history: byId('clearHistory'),
    currentAction: byId('currentAction'),
    rawAction: byId('rawAction'),
    appliedAction: byId('appliedAction'),
    lastReward: byId('lastReward'),
    survivalTime: byId('survivalTime'),
    episodeNumber: byId('episodeNumber'),
    reinforcement: byId('reinforcement'),
    brainInput: byId('brainInput'),
    brainOutput: byId('brainOutput'),
    neuralWindowMs: byId('neuralWindowMs'),
    brainMs: byId('brainMs'),
    computeSeconds: byId('computeSeconds'),
    totalSpikes: byId('totalSpikes'),
    walkingSpikes: byId('walkingSpikes'),
    leftHz: byId('leftHz'),
    rightHz: byId('rightHz'),
    foodOdorSpikes: byId('foodOdorSpikes'),
    dangerOdorSpikes: byId('dangerOdorSpikes'),
    foodLeft: byId('foodLeft'),
    episodeFood: byId('episodeFood'),
    totalFood: byId('totalFood'),
    totalDeaths: byId('totalDeaths'),
    enemyCount: byId('enemyCount'),
    decisionTicks: byId('decisionTicks'),
    worldTicks: byId('worldTicks'),
    powerState: byId('powerState'),
    cumulativeReward: byId('cumulativeReward'),
  };

  const COLS = 19;
  const ROWS = 14;
  const CELL_X = canvas.width / COLS;
  const CELL_Y = canvas.height / ROWS;
  const VALID_ACTIONS = new Set(['TURN_LEFT', 'TURN_RIGHT', 'FORWARD', 'HOLD']);
  const NEURAL_WINDOW_MS = 50;
  const LIVE_RELAY = 'https://neurofly-curriculum-relay.onrender.com/events';
  const LIVE_SILENCE_MS = 3000;
  const LIVE_RECONNECT_MS = 15000;
  const FALLBACK_REFRESH_MS = 60000;

  let currentView = null;
  let currentEvent = null;
  let liveSilenceTimer = null;
  let liveWatchdogTimer = null;
  let liveReconnectTimer = null;
  let liveSource = null;
  let liveSequence = -1;
  let liveSeen = false;
  let flashUntil = 0;
  let flashText = '';
  let totalClockBase = 0;
  let totalClockAnchor = 0;
  let lastLiveStateAt = 0;
  let fallbackEpisode = null;
  let fallbackEpisodeOffset = 0;
  let fallbackLastSurvival = 0;

  const actionName = action => ({
    TURN_LEFT: '左轉',
    TURN_RIGHT: '右轉',
    FORWARD: '前進',
    HOLD: '停留',
  })[action] || action || '—';

  const reinforcementName = value => ({
    reward: '正向獎勵',
    aversive: '負向刺激',
    none: '無',
  })[value] || value || '—';

  function finiteNumber(value) {
    const number = Number(value);
    return Number.isFinite(number) ? number : null;
  }

  function formatSeconds(value) {
    const seconds = finiteNumber(value);
    if (seconds == null || seconds < 0) return '—';
    if (seconds < 60) return `${seconds.toFixed(1)} 秒`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes} 分 ${(seconds % 60).toFixed(1)} 秒`;
    const hours = Math.floor(minutes / 60);
    return `${hours} 小時 ${minutes % 60} 分 ${Math.floor(seconds % 60)} 秒`;
  }

  function formatNeuralDurationMs(value) {
    const milliseconds = finiteNumber(value);
    if (milliseconds == null || milliseconds < 0) return '—';
    return formatSeconds(milliseconds / 1000);
  }

  function formatComputeSeconds(value) {
    const seconds = finiteNumber(value);
    if (seconds == null || seconds < 0) return '—';
    if (seconds < 1) return `${Math.round(seconds * 1000)} 毫秒`;
    return `${seconds.toFixed(2)} 秒`;
  }

  function formatCount(value) {
    const number = finiteNumber(value);
    return number == null ? '—' : Math.round(number).toLocaleString('zh-TW');
  }

  function formatReward(value) {
    const number = finiteNumber(value);
    if (number == null) return '—';
    return `${number >= 0 ? '+' : ''}${number.toFixed(2)}`;
  }

  function formatHz(value) {
    const number = finiteNumber(value);
    return number == null ? '—' : `${number.toFixed(2)} Hz`;
  }

  function formatOdorLevel(value) {
    const number = finiteNumber(value);
    if (number == null) return '—';
    return `${(Math.max(0, Math.min(1, number)) * 100).toFixed(1)}%`;
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
    const trajectory = Array.isArray(payload.trajectory) ? payload.trajectory : [];
    return neuralStateIsVerified(payload.final_state || trajectory[trajectory.length - 1]);
  }

  function setConnection(state, text) {
    ui.connection.dataset.state = state;
    ui.connection.textContent = text;
  }

  function syncTotalClock(view, { live = false } = {}) {
    const authoritative = Number(view?.total_active_seconds);
    const survival = Number(view?.survival_seconds);
    const episode = Number(view?.episode);

    if (Number.isFinite(authoritative) && authoritative >= 0) {
      totalClockBase = authoritative;
      if (Number.isFinite(episode)) fallbackEpisode = episode;
      if (Number.isFinite(survival) && survival >= 0) {
        fallbackLastSurvival = survival;
        fallbackEpisodeOffset = Math.max(0, authoritative - survival);
      }
    } else if (Number.isFinite(survival) && survival >= 0) {
      if (fallbackEpisode === null) {
        fallbackEpisode = Number.isFinite(episode) ? episode : null;
      } else if (Number.isFinite(episode) && episode !== fallbackEpisode) {
        fallbackEpisodeOffset += fallbackLastSurvival;
        fallbackEpisode = episode;
        fallbackLastSurvival = 0;
      }
      fallbackLastSurvival = Math.max(fallbackLastSurvival, survival);
      totalClockBase = fallbackEpisodeOffset + survival;
    }

    totalClockAnchor = Date.now();
    if (live) lastLiveStateAt = Date.now();
    renderTotalClock();
  }

  function renderTotalClock() {
    let seconds = totalClockBase;
    if (
      liveSeen &&
      totalClockAnchor > 0 &&
      lastLiveStateAt > 0 &&
      Date.now() - lastLiveStateAt <= LIVE_SILENCE_MS
    ) {
      seconds += Math.max(0, Date.now() - totalClockAnchor) / 1000;
    }
    ui.total.textContent = formatSeconds(seconds);
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

    ctx.fillStyle = 'rgba(216,255,115,.10)';
    ctx.shadowColor = 'rgba(216,255,115,.52)';
    ctx.shadowBlur = 20;
    ctx.beginPath();
    ctx.arc(0, 0, 22, 0, Math.PI * 2);
    ctx.fill();
    ctx.shadowBlur = 0;

    ctx.rotate(angle);
    ctx.scale(1.15, 1.15);
    ctx.fillStyle = 'rgba(220,255,245,.78)';
    ctx.strokeStyle = 'rgba(143,242,183,.98)';
    ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.ellipse(-4, -13, 13, 7, -.5, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    ctx.beginPath(); ctx.ellipse(-4, 13, 13, 7, .5, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    ctx.fillStyle = '#d8ff73';
    ctx.shadowColor = 'rgba(216,255,115,.35)';
    ctx.shadowBlur = 8;
    ctx.beginPath(); ctx.ellipse(0, 0, 16, 9, 0, 0, Math.PI * 2); ctx.fill();
    ctx.shadowBlur = 0;
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
    const color = index === 0 ? '#ff6678' : '#cb79ff';
    const halo = index === 0 ? 'rgba(255,102,120,.20)' : 'rgba(203,121,255,.17)';

    ctx.save();
    ctx.translate(cx, cy);

    ctx.fillStyle = halo;
    ctx.shadowColor = color;
    ctx.shadowBlur = 24;
    ctx.beginPath();
    ctx.arc(0, 1, 23, 0, Math.PI * 2);
    ctx.fill();

    ctx.scale(1.25, 1.25);
    ctx.fillStyle = color;
    ctx.shadowColor = color;
    ctx.shadowBlur = 16;
    ctx.beginPath();
    ctx.arc(0, -3, 14, Math.PI, 0);
    ctx.lineTo(14, 10);
    ctx.quadraticCurveTo(8, 15, 3, 10);
    ctx.quadraticCurveTo(-2, 15, -7, 10);
    ctx.quadraticCurveTo(-11, 14, -14, 10);
    ctx.closePath();
    ctx.fill();
    ctx.shadowBlur = 0;

    ctx.fillStyle = '#f8fbfa';
    ctx.beginPath(); ctx.arc(-5, -4, 4, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.arc(5, -4, 4, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#17231e';
    ctx.beginPath(); ctx.arc(-5, -4, 1.65, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.arc(5, -4, 1.65, 0, Math.PI * 2); ctx.fill();
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
    ctx.fillText('MALECNS', canvas.width / 2, canvas.height / 2 - 12);
    ctx.fillStyle = '#a8bbb3';
    ctx.font = '16px system-ui, sans-serif';
    ctx.fillText(message, canvas.width / 2, canvas.height / 2 + 26);
  }

  function draw(view) {
    if (!neuralStateIsVerified(view)) return;
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

  function updateGoalHud(view, { live = false } = {}) {
    const history = Array.isArray(view?.clear_history) ? view.clear_history : [];
    syncTotalClock(view, { live });
    ui.first.textContent = formatSeconds(view?.first_clear_seconds);
    ui.latest.textContent = formatSeconds(view?.latest_clear_seconds);
    ui.best.textContent = formatSeconds(view?.best_clear_seconds);
    ui.clears.textContent = formatCount(view?.total_clears ?? history.length ?? 0);
    ui.history.textContent = history.length
      ? history.slice(-5).map(item => `第 ${item.clear_index} 次：${formatSeconds(item.seconds)} · ${item.ticks} 次決策`).join('　')
      : '尚未破關';
  }

  function updateTelemetry(view) {
    const brain = view.brain || {};
    const telemetry = brain.telemetry || {};
    const olfaction = telemetry.olfaction || {};
    const raw = view.raw_brain_action || view.decision_action || view.last_action;
    const applied = view.applied_action || view.last_action;

    ui.currentAction.textContent = actionName(applied);
    ui.rawAction.textContent = actionName(raw);
    ui.appliedAction.textContent = actionName(applied);
    ui.lastReward.textContent = formatReward(view.last_reward);
    ui.survivalTime.textContent = formatSeconds(view.survival_seconds);
    ui.episodeNumber.textContent = view.episode == null ? '—' : `第 ${formatCount(view.episode)} 局`;
    ui.reinforcement.textContent = reinforcementName(view.reinforcement || telemetry.reinforcement);

    ui.neuralWindowMs.textContent = `${NEURAL_WINDOW_MS} 毫秒`;
    ui.brainMs.textContent = formatNeuralDurationMs(telemetry.brain_ms);
    ui.computeSeconds.textContent = formatComputeSeconds(telemetry.compute_seconds);
    ui.totalSpikes.textContent = formatCount(telemetry.total_spikes);
    ui.walkingSpikes.textContent = formatCount(telemetry.walking_spikes);
    ui.leftHz.textContent = formatHz(telemetry.left_hz);
    ui.rightHz.textContent = formatHz(telemetry.right_hz);
    ui.foodOdorSpikes.textContent = formatCount(telemetry.food_odor_spikes);
    ui.dangerOdorSpikes.textContent = formatCount(telemetry.danger_odor_spikes);

    ui.foodLeft.textContent = formatCount(view.food_left);
    ui.episodeFood.textContent = formatCount(view.episode_food);
    ui.totalFood.textContent = formatCount(view.total_food);
    ui.totalDeaths.textContent = formatCount(view.total_deaths);
    ui.enemyCount.textContent = formatCount((view.enemies || []).length);
    ui.decisionTicks.textContent = formatCount(view.ticks);
    ui.worldTicks.textContent = formatCount(view.total_world_ticks);
    ui.powerState.textContent = Number(view.power_ticks) > 0 ? `啟動 · 剩餘 ${formatCount(view.power_ticks)} 步` : '未啟動';
    ui.cumulativeReward.textContent = formatReward(view.cumulative_reward);

    ui.brainInput.textContent = [
      '視覺：迷宮 RGB 畫面',
      `食物嗅覺 左 ${formatOdorLevel(olfaction.food_left)}／右 ${formatOdorLevel(olfaction.food_right)}`,
      `危險嗅覺 左 ${formatOdorLevel(olfaction.danger_left)}／右 ${formatOdorLevel(olfaction.danger_right)}`,
    ].join(' · ');

    ui.brainOutput.textContent = view.action_overridden === true && raw !== applied
      ? `MaleCNS 原始輸出「${actionName(raw)}」，防停滯機制實際套用「${actionName(applied)}」`
      : `MaleCNS 輸出「${actionName(raw)}」`;
  }

  function flashForState(view) {
    if (view.last_event === 'captured') {
      flashText = '被敵人抓到 · 重新開始';
      flashUntil = Date.now() + 900;
    } else if (view.last_event === 'maze_cleared') {
      flashText = `成功破關 · ${formatSeconds(view.latest_clear_seconds)}`;
      flashUntil = Date.now() + 1400;
    } else if (view.last_event === 'energy_food') {
      flashText = '取得能量食物';
      flashUntil = Date.now() + 650;
    }
  }

  function decisionLabel(view) {
    const raw = view.raw_brain_action || view.decision_action || view.last_action;
    const applied = view.applied_action || view.last_action;
    if (view.action_overridden === true && raw !== applied) {
      return `MaleCNS 原始：${actionName(raw)} → 防停滯套用：${actionName(applied)}`;
    }
    return `MaleCNS：${actionName(raw)}`;
  }

  function stateStatus(event, view) {
    const kind = view.state_kind || 'neural_decision';
    if (kind === 'world_tick') {
      return `世界持續運作 · 世界步 ${view.total_world_ticks ?? '—'} · ${decisionLabel(view)} · 第 ${view.episode} 局`;
    }
    if (kind === 'episode_reset') {
      return `新一局已開始 · 第 ${view.episode} 局`;
    }
    if (kind === 'stale_decision') {
      return `MaleCNS 過期決策「${actionName(view.decision_action || view.last_action)}」已丟棄 · 第 ${view.episode} 局`;
    }
    return `即時運作 · 決策 ${event?.sequence ?? '—'} · ${decisionLabel(view)} · 第 ${view.episode} 局`;
  }

  function renderState(view, event, { live = false } = {}) {
    if (!neuralStateIsVerified(view)) return;
    flashForState(view);
    draw(view);
    updateGoalHud(view, { live });
    updateTelemetry(view);
    ui.badge.textContent = live ? 'MALECNS · 即時運作中' : 'MALECNS · 最近驗證狀態';
    ui.status.textContent = live
      ? stateStatus(event, view)
      : `顯示最近已驗證狀態 · 第 ${view.episode} 局 · 等待即時資料`;
  }

  function clearLiveWatchdog() {
    clearTimeout(liveWatchdogTimer);
    liveWatchdogTimer = null;
  }

  function scheduleLiveReconnect(delay = 500) {
    clearTimeout(liveReconnectTimer);
    liveReconnectTimer = setTimeout(() => {
      liveReconnectTimer = null;
      connectLive();
    }, delay);
  }

  function armLiveWatchdog() {
    clearLiveWatchdog();
    liveWatchdogTimer = setTimeout(() => {
      liveWatchdogTimer = null;
      if (liveSource) {
        liveSource.close();
        liveSource = null;
      }
      setConnection('waiting', '即時資料逾時');
      ui.status.textContent = '即時資料逾時 · 正在重新連線到 MaleCNS relay…';
      scheduleLiveReconnect(250);
    }, LIVE_RECONNECT_MS);
  }

  function showLiveState(event) {
    const view = event?.state;
    if (event?.schema !== 'neurofly-live-state-v1' || event?.verified !== true || event?.backend !== 'malecns') return;
    if (!neuralStateIsVerified(view)) return;
    const seq = Number(event.relay_sequence ?? event.sequence ?? -1);
    if (Number.isFinite(seq) && seq <= liveSequence) return;

    liveSequence = seq;
    liveSeen = true;
    currentView = view;
    currentEvent = event;
    lastLiveStateAt = Date.now();
    armLiveWatchdog();
    clearTimeout(liveSilenceTimer);
    setConnection('live', 'MaleCNS 即時連線');
    renderState(view, event, { live: true });

    liveSilenceTimer = setTimeout(() => {
      renderTotalClock();
      setConnection('waiting', '等待下一個神經狀態');
      ui.status.textContent = `等待下一個已驗證狀態 · MaleCNS 可能正在運算 · 第 ${currentView?.episode || '—'} 局`;
    }, LIVE_SILENCE_MS);
  }

  async function loadFallback() {
    try {
      const response = await fetch(`./malecns-state.json?t=${Date.now()}`, { cache: 'no-store' });
      if (!response.ok) return;
      const payload = await response.json();
      if (!payloadIsVerified(payload) || liveSeen) return;
      const trajectory = Array.isArray(payload.trajectory) ? payload.trajectory : [];
      const view = payload.final_state || trajectory[trajectory.length - 1];
      currentView = view;
      currentEvent = null;
      renderState(view, null, { live: false });
      setConnection('waiting', '最近驗證狀態');
    } catch (_) {
      if (!liveSeen) {
        setConnection('offline', '備援資料讀取失敗');
        ui.status.textContent = '目前無法讀取備援狀態 · 持續嘗試即時連線';
      }
    }
  }

  function connectLive({ manual = false } = {}) {
    clearTimeout(liveReconnectTimer);
    liveReconnectTimer = null;
    clearLiveWatchdog();
    if (liveSource) liveSource.close();

    if (manual) {
      liveSequence = -1;
      liveSeen = false;
      setConnection('waiting', '正在重新連線');
      ui.status.textContent = '正在重新建立 MaleCNS 即時連線…';
    }

    const source = new EventSource(LIVE_RELAY);
    liveSource = source;

    source.addEventListener('malecns', event => {
      if (source !== liveSource) return;
      try {
        showLiveState(JSON.parse(event.data));
      } catch (_) {
        ui.status.textContent = '收到無法解析的即時資料 · 等待下一筆狀態';
      }
    });

    source.onopen = () => {
      if (source !== liveSource) return;
      armLiveWatchdog();
      if (!liveSeen) {
        ui.badge.textContent = 'MALECNS · 即時連線已建立';
        setConnection('waiting', '連線已建立');
        ui.status.textContent = '即時連線已建立 · 等待已驗證的 MaleCNS 狀態';
      }
    };

    source.onerror = () => {
      if (source !== liveSource) return;
      source.close();
      liveSource = null;
      clearLiveWatchdog();
      setConnection('offline', '即時連線重連中');
      ui.status.textContent = liveSeen ? '即時連線中斷 · 正在重新連接…' : '尚未取得即時資料 · 正在重新連接…';
      scheduleLiveReconnect(1000);
    };
  }

  ui.reconnectLive.addEventListener('click', () => connectLive({ manual: true }));

  ui.neuralWindowMs.textContent = `${NEURAL_WINDOW_MS} 毫秒`;
  drawWaiting('正在連接即時神經與世界狀態…');
  setConnection('waiting', '正在連線');
  loadFallback();
  connectLive();
  setInterval(renderTotalClock, 250);
  setInterval(() => { if (!liveSeen) loadFallback(); }, FALLBACK_REFRESH_MS);
})();
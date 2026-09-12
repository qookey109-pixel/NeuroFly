(() => {
  const canvas = document.getElementById('mazeCanvas');
  const ctx = canvas.getContext('2d');
  const ui = {
    badge: document.getElementById('brainBadge'),
    status: document.getElementById('runStatus'),
    total: document.getElementById('totalTime'),
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
  const LIVE_RELAY = 'https://neurofly-curriculum-relay.onrender.com/events';
  const LIVE_SILENCE_MS = 3000;
  const FALLBACK_REFRESH_MS = 60000;

  let currentView = null;
  let liveSilenceTimer = null;
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

  function formatSeconds(value) {
    if (value == null || value === '') return '—';
    const seconds = Number(value);
    if (!Number.isFinite(seconds) || seconds < 0) return '—';
    if (seconds < 60) return `${seconds.toFixed(1)} 秒`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes} 分 ${(seconds % 60).toFixed(1)} 秒`;
    const hours = Math.floor(minutes / 60);
    return `${hours} 小時 ${minutes % 60} 分 ${Math.floor(seconds % 60)} 秒`;
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
    return neuralStateIsVerified(payload.final_state || payload.trajectory?.at?.(-1));
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
    ui.clears.textContent = String(view?.total_clears || history.length || 0);
    ui.history.textContent = history.length
      ? history.slice(-5).map(item => `第 ${item.clear_index} 次：${formatSeconds(item.seconds)} · ${item.ticks} 次決策`).join('　')
      : '尚未破關';
  }

  function flashForState(view) {
    if (view.last_event === 'captured') {
      flashText = '被敵人抓到 · 重新開始';
      flashUntil = Date.now() + 900;
    } else if (view.last_event === 'maze_cleared') {
      flashText = `成功破關 · ${formatSeconds(view.latest_clear_seconds)}`;
      flashUntil = Date.now() + 1400;
    }
  }

  function stateStatus(event, view) {
    const kind = view.state_kind || 'neural_decision';
    if (kind === 'world_tick') {
      return `世界持續運作 · 世界步 ${view.total_world_ticks ?? '—'} · MaleCNS 正在運算 · 第 ${view.episode} 局`;
    }
    if (kind === 'episode_reset') {
      return `新一局已開始 · 第 ${view.episode} 局`;
    }
    if (kind === 'stale_decision') {
      return `MaleCNS 過期決策「${actionName(view.decision_action || view.last_action)}」已丟棄 · 第 ${view.episode} 局`;
    }
    return `MaleCNS 即時運作 · 決策 ${event.sequence} · ${actionName(view.decision_action || view.last_action)} · 第 ${view.episode} 局`;
  }

  function showLiveState(event) {
    const view = event?.state;
    if (event?.schema !== 'neurofly-live-state-v1' || event?.verified !== true || event?.backend !== 'malecns') return;
    if (!neuralStateIsVerified(view)) return;
    const seq = Number(event.relay_sequence ?? event.sequence ?? -1);
    if (Number.isFinite(seq) && seq <= liveSequence) return;
    liveSequence = seq;
    liveSeen = true;
    clearTimeout(liveSilenceTimer);
    currentView = view;
    flashForState(view);
    draw(view);
    updateGoalHud(view, { live: true });
    ui.badge.textContent = 'MALECNS · 即時運作中';
    ui.status.textContent = stateStatus(event, view);
    liveSilenceTimer = setTimeout(() => {
      renderTotalClock();
      ui.status.textContent = `等待下一個已驗證狀態 · MaleCNS 可能正在運算 · 第 ${currentView?.episode || '—'} 局`;
    }, LIVE_SILENCE_MS);
  }

  async function loadFallback() {
    try {
      const response = await fetch(`./malecns-state.json?t=${Date.now()}`, { cache: 'no-store' });
      if (!response.ok) return;
      const payload = await response.json();
      if (!payloadIsVerified(payload) || liveSeen) return;
      const view = payload.final_state || payload.trajectory[payload.trajectory.length - 1];
      currentView = view;
      draw(view);
      updateGoalHud(view, { live: false });
      ui.badge.textContent = 'MALECNS · 最近驗證狀態';
      ui.status.textContent = `等待 MaleCNS 即時資料 · 第 ${view.episode} 局`;
    } catch (_) {
      // 靜態狀態只是備援；SSE 才是主要即時來源。
    }
  }

  function connectLive() {
    const source = new EventSource(LIVE_RELAY);
    source.addEventListener('malecns', event => {
      try { showLiveState(JSON.parse(event.data)); } catch (_) {}
    });
    source.onopen = () => {
      if (!liveSeen) {
        ui.badge.textContent = 'MALECNS · 即時連線已建立';
        ui.status.textContent = '即時連線已建立 · 等待已驗證的 MaleCNS 狀態';
      }
    };
    source.onerror = () => {
      if (liveSeen) ui.status.textContent = '即時連線重新連接中…';
      else ui.badge.textContent = 'MALECNS · 連線中';
    };
  }

  drawWaiting('正在連接即時神經與世界狀態…');
  loadFallback();
  connectLive();
  setInterval(renderTotalClock, 250);
  setInterval(() => { if (!liveSeen) loadFallback(); }, FALLBACK_REFRESH_MS);
})();

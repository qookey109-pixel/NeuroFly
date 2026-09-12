(() => {
  const target = document.getElementById('allClearHistory');
  if (!target) return;

  const LIVE_RELAY = 'https://neurofly-curriculum-relay.onrender.com/events';

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

  function render(history) {
    if (!Array.isArray(history) || history.length === 0) {
      target.textContent = '尚未破關';
      return;
    }
    target.innerHTML = history
      .map(item => {
        const index = Number(item?.clear_index) || 0;
        const episode = Number(item?.episode);
        const ticks = Number(item?.ticks);
        const extras = [];
        if (Number.isFinite(episode)) extras.push(`第 ${episode} 局`);
        if (Number.isFinite(ticks)) extras.push(`${ticks} 次決策`);
        const suffix = extras.length ? ` · ${extras.join(' · ')}` : '';
        return `<div>第 ${index} 次：<strong>${formatSeconds(item?.seconds)}</strong>${suffix}</div>`;
      })
      .join('');
    target.scrollTop = target.scrollHeight;
  }

  async function loadFallback() {
    try {
      const response = await fetch(`./malecns-state.json?t=${Date.now()}`, { cache: 'no-store' });
      if (!response.ok) return;
      const payload = await response.json();
      const view = payload?.final_state || payload?.trajectory?.[payload.trajectory.length - 1];
      render(view?.clear_history);
    } catch (_) {}
  }

  loadFallback();

  try {
    const source = new EventSource(LIVE_RELAY);
    source.addEventListener('malecns', event => {
      try {
        const payload = JSON.parse(event.data);
        render(payload?.state?.clear_history);
      } catch (_) {}
    });
  } catch (_) {}
})();

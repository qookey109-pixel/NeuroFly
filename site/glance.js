(() => {
  const byId = id => document.getElementById(id);
  const status = byId('runStatus');
  if (!status) return;

  const MAX_POINTS = 36;
  const series = {
    reward: [],
    computeMs: [],
    leftHz: [],
    rightHz: [],
  };

  let lastSignature = '';

  function numberFrom(text) {
    if (!text) return null;
    const value = Number.parseFloat(String(text).replace(/,/g, '').replace('+', ''));
    return Number.isFinite(value) ? value : null;
  }

  function computeMilliseconds(text) {
    const value = numberFrom(text);
    if (value == null) return null;
    return String(text).includes('秒') ? value * 1000 : value;
  }

  function pushPoint(name, value) {
    if (value == null) return;
    const target = series[name];
    target.push(value);
    if (target.length > MAX_POINTS) target.splice(0, target.length - MAX_POINTS);
  }

  function bounds(values, includeZero = false) {
    if (!values.length) return { min: 0, max: 1 };
    let min = Math.min(...values);
    let max = Math.max(...values);
    if (includeZero) {
      min = Math.min(0, min);
      max = Math.max(0, max);
    }
    if (min === max) {
      const pad = Math.max(1, Math.abs(min) * 0.12);
      min -= pad;
      max += pad;
    }
    return { min, max };
  }

  function makePath(values, width, height, range) {
    if (!values.length) return '';
    const padX = 3;
    const padY = 4;
    const usableW = width - padX * 2;
    const usableH = height - padY * 2;
    const span = range.max - range.min || 1;
    return values.map((value, index) => {
      const x = values.length === 1
        ? width / 2
        : padX + (index / (values.length - 1)) * usableW;
      const y = padY + (1 - (value - range.min) / span) * usableH;
      return `${index === 0 ? 'M' : 'L'}${x.toFixed(2)},${y.toFixed(2)}`;
    }).join(' ');
  }

  function renderSingle(pathId, values, { includeZero = false, zeroId = null } = {}) {
    const path = byId(pathId);
    if (!path) return;
    const width = 240;
    const height = 50;
    const range = bounds(values, includeZero);
    path.setAttribute('d', makePath(values, width, height, range));

    if (zeroId) {
      const zero = byId(zeroId);
      if (zero) {
        if (range.min <= 0 && range.max >= 0) {
          const y = 4 + (1 - (0 - range.min) / (range.max - range.min || 1)) * 42;
          zero.setAttribute('y1', y.toFixed(2));
          zero.setAttribute('y2', y.toFixed(2));
          zero.removeAttribute('hidden');
        } else {
          zero.setAttribute('hidden', '');
        }
      }
    }
  }

  function renderMotor() {
    const left = byId('motorLeftTrendPath');
    const right = byId('motorRightTrendPath');
    if (!left || !right) return;
    const combined = [...series.leftHz, ...series.rightHz];
    const range = bounds(combined, true);
    left.setAttribute('d', makePath(series.leftHz, 240, 50, range));
    right.setAttribute('d', makePath(series.rightHz, 240, 50, range));
  }

  function sample() {
    const rewardText = byId('cumulativeReward')?.textContent || '';
    const computeText = byId('computeSeconds')?.textContent || '';
    const leftText = byId('leftHz')?.textContent || '';
    const rightText = byId('rightHz')?.textContent || '';
    const signature = [status.textContent, rewardText, computeText, leftText, rightText].join('|');
    if (signature === lastSignature) return;
    lastSignature = signature;

    pushPoint('reward', numberFrom(rewardText));
    pushPoint('computeMs', computeMilliseconds(computeText));
    pushPoint('leftHz', numberFrom(leftText));
    pushPoint('rightHz', numberFrom(rightText));

    renderSingle('rewardTrendPath', series.reward, { includeZero: true, zeroId: 'rewardZeroLine' });
    renderSingle('computeTrendPath', series.computeMs);
    renderMotor();

    const sampleCount = byId('trendSampleCount');
    if (sampleCount) sampleCount.textContent = `${Math.max(series.computeMs.length, series.reward.length)} / ${MAX_POINTS}`;
  }

  const observer = new MutationObserver(() => queueMicrotask(sample));
  observer.observe(status, { childList: true, characterData: true, subtree: true });
  sample();
})();

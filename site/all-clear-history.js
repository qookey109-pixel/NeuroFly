(() => {
  const target = document.getElementById('allClearHistory');
  if (!target) return;

  const LIVE_RELAY = 'https://neurofly-curriculum-relay.onrender.com/events';
  const PROPRIOCEPTION_SEMANTICS = './proprioception-semantics.json';

  const candidateLabels = {
    hook_extension_sensitive: 'extension-sensitive 候選',
    hook_flexion_sensitive: 'flexion-sensitive 候選',
  };

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

  function ensureProprioceptionPanel() {
    let panel = document.getElementById('proprioceptionObservability');
    if (panel) return panel;

    const rail = document.querySelector('.brain-rail');
    if (!rail) return null;

    panel = document.createElement('section');
    panel.id = 'proprioceptionObservability';
    panel.className = 'rail-section proprioception-observability-section';
    panel.setAttribute('aria-label', 'FeCO proprioception systematic-type observability');
    panel.innerHTML = `
      <div class="rail-heading compact-rail-heading">
        <div><span>PROPRIOCEPTION / CONTROL PLANE</span><h2>FeCO 方向語意狀態</h2></div>
      </div>
      <div class="brain-sentence">
        <span>證據狀態</span>
        <p id="proprioceptionSemanticStatus">載入中…</p>
      </div>
      <div class="telemetry-lines">
        <div><span>Channel A</span><strong id="proprioceptionChannelA">—</strong></div>
        <div><span>Channel B</span><strong id="proprioceptionChannelB">—</strong></div>
        <div><span>工程 hook channel</span><strong id="proprioceptionEngineeringBinding">—</strong></div>
        <div><span>Runtime binding</span><strong id="proprioceptionRuntimeLock">—</strong></div>
        <div><span>Current calibration</span><strong id="proprioceptionCalibrationLock">—</strong></div>
        <div><span>Neural payload</span><strong id="proprioceptionNeuralEligibility">—</strong></div>
      </div>
      <div class="brain-sentence">
        <span>解讀</span>
        <p id="proprioceptionSemanticNote">這裡是人類觀察用 control plane，不是 MaleCNS 感覺輸入。</p>
      </div>
    `;

    const anchor = document.querySelector('.world-detail-section');
    rail.insertBefore(panel, anchor || null);
    return panel;
  }

  function setText(id, value) {
    const node = document.getElementById(id);
    if (node) node.textContent = value;
  }

  function formatCandidate(name, record) {
    if (!record || typeof record !== 'object') return '—';
    const systematicType = record.systematic_type || '—';
    const candidate = candidateLabels[record.candidate_function] || record.candidate_function || '—';
    const evidence = record.evidence_level || '—';
    return `${systematicType} · ${candidate} · ${evidence}（推論）`;
  }

  function renderProprioceptionSemantics(contract) {
    ensureProprioceptionPanel();
    const valid = contract
      && contract.schema === 'neurofly-proprioception-systematic-type-semantics-v0.1'
      && contract.plane === 'control-plane-only-not-neural-input'
      && contract.systematic_type_polarity_resolved === false
      && contract.neural_payload_eligible === false;

    if (!valid) {
      setText('proprioceptionSemanticStatus', '語意快照驗證失敗');
      setText('proprioceptionRuntimeLock', 'FAIL CLOSED');
      setText('proprioceptionCalibrationLock', 'FAIL CLOSED');
      setText('proprioceptionNeuralEligibility', '禁止');
      return;
    }

    const channels = contract.opaque_systematic_channels || {};
    const engineering = contract.engineering_receptor_channels || {};
    const extensionBinding = engineering.hook_extension?.systematic_type_binding;
    const flexionBinding = engineering.hook_flexion?.systematic_type_binding;
    const bindingsOpen = extensionBinding != null || flexionBinding != null;

    setText(
      'proprioceptionSemanticStatus',
      `${contract.status} · direct SNpp39/SNpp41 polarity crosswalk unresolved`
    );
    setText(
      'proprioceptionChannelA',
      formatCandidate('hook_direction_channel_A', channels.hook_direction_channel_A)
    );
    setText(
      'proprioceptionChannelB',
      formatCandidate('hook_direction_channel_B', channels.hook_direction_channel_B)
    );
    setText(
      'proprioceptionEngineeringBinding',
      bindingsOpen ? '⚠ systematic type binding detected' : 'hook_extension / hook_flexion · 未綁 systematic type'
    );
    setText(
      'proprioceptionRuntimeLock',
      contract.runtime_transduction_enabled === false
        && channels.hook_direction_channel_A?.runtime_routable === false
        && channels.hook_direction_channel_B?.runtime_routable === false
        ? 'LOCKED'
        : 'FAIL CLOSED'
    );
    setText(
      'proprioceptionCalibrationLock',
      contract.current_calibration_authorized === false ? 'LOCKED' : 'FAIL CLOSED'
    );
    setText(
      'proprioceptionNeuralEligibility',
      contract.neural_payload_eligible === false ? '否 · control plane only' : 'FAIL CLOSED'
    );
    setText(
      'proprioceptionSemanticNote',
      'A/B 只保留目前的 physiology-supported inference；沒有 executable hook_extension/flexion → SNpp39/41 alias，也沒有 proprioceptive current。'
    );
  }

  async function loadProprioceptionSemantics() {
    ensureProprioceptionPanel();
    try {
      const response = await fetch(`${PROPRIOCEPTION_SEMANTICS}?t=${Date.now()}`, { cache: 'no-store' });
      if (!response.ok) throw new Error('semantic snapshot unavailable');
      renderProprioceptionSemantics(await response.json());
    } catch (_) {
      setText('proprioceptionSemanticStatus', '語意快照無法載入');
      setText('proprioceptionRuntimeLock', 'FAIL CLOSED');
      setText('proprioceptionCalibrationLock', 'FAIL CLOSED');
      setText('proprioceptionNeuralEligibility', '禁止');
    }
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
  loadProprioceptionSemantics();

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

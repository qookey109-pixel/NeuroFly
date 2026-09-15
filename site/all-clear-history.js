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

  function formatReceptorLevel(value) {
    const number = Number(value);
    if (!Number.isFinite(number) || number < 0 || number > 1) return '—';
    return `${(number * 100).toFixed(1)}%`;
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
        <div><span>PROPRIOCEPTION</span><h2>FeCO receptor / control plane</h2></div>
      </div>
      <div class="brain-sentence">
        <span>LIVE RECEPTOR INPUT</span>
        <p id="proprioceptionLiveStatus">等待本次 neural handoff receptor 資料…</p>
      </div>
      <div class="telemetry-lines">
        <div><span>Hook extension</span><strong id="proprioceptionHookExtension">—</strong></div>
        <div><span>Hook flexion</span><strong id="proprioceptionHookFlexion">—</strong></div>
        <div><span>Club motion</span><strong id="proprioceptionClubMotion">—</strong></div>
        <div><span>Club vibration</span><strong id="proprioceptionClubVibration">—</strong></div>
      </div>
      <div class="brain-sentence">
        <span>證據狀態 / CONTROL PLANE</span>
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
        <p id="proprioceptionSemanticNote">Live receptor 數值與 SNpp39/SNpp41 候選語意分離；control plane 不回流成 neural input。</p>
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

  function renderLiveProprioception(view) {
    ensureProprioceptionPanel();
    const record = view?.human_diagnostics?.proprioception;
    const channels = record?.channels;
    const values = channels && [
      channels.hook_extension,
      channels.hook_flexion,
      channels.club_motion,
      channels.club_vibration,
    ];
    const validLevels = Array.isArray(values)
      && values.every(value => Number.isFinite(Number(value)) && Number(value) >= 0 && Number(value) <= 1);
    const valid = record
      && record.source === 'latest-neural-handoff-receptor-domain'
      && record.model === 'neurofly-feco-motion-proxy-v0.1'
      && record.encoding === 'virtual-joint-motion-only-proxy'
      && record.stimulation_enabled === false
      && record.runtime_transduction_enabled === false
      && record.systematic_type_mapping_exposed === false
      && validLevels;

    if (!valid) {
      setText('proprioceptionLiveStatus', '即時 receptor 診斷不可用 · FAIL CLOSED');
      setText('proprioceptionHookExtension', '—');
      setText('proprioceptionHookFlexion', '—');
      setText('proprioceptionClubMotion', '—');
      setText('proprioceptionClubVibration', '—');
      return;
    }

    setText('proprioceptionLiveStatus', '本次 neural handoff 的 receptor-domain 輸入 · human diagnostics only');
    setText('proprioceptionHookExtension', formatReceptorLevel(channels.hook_extension));
    setText('proprioceptionHookFlexion', formatReceptorLevel(channels.hook_flexion));
    setText('proprioceptionClubMotion', formatReceptorLevel(channels.club_motion));
    setText('proprioceptionClubVibration', formatReceptorLevel(channels.club_vibration));
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
      '上方 live 數值只代表工程 receptor channel；A/B 只保留 physiology-supported inference。沒有 executable hook_extension/flexion → SNpp39/41 alias，也沒有 proprioceptive current。'
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
      renderLiveProprioception(view);
    } catch (_) {}
  }

  loadFallback();
  loadProprioceptionSemantics();

  try {
    const source = new EventSource(LIVE_RELAY);
    source.addEventListener('malecns', event => {
      try {
        const payload = JSON.parse(event.data);
        const view = payload?.state;
        render(view?.clear_history);
        renderLiveProprioception(view);
      } catch (_) {}
    });
  } catch (_) {}
})();

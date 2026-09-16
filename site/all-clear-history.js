(() => {
  const target = document.getElementById('allClearHistory');
  if (!target) return;

  const LIVE_RELAY = 'https://neurofly-curriculum-relay.onrender.com/events';
  const PROPRIOCEPTION_SEMANTICS = './proprioception-semantics.json';
  const TEMPORAL_SCHEMA = 'neurofly-proprioception-temporal-observability-v0.1';
  const TEMPORAL_SOURCE = 'verified-neural-handoff-receptor-domain';
  const TEMPORAL_MAX_CAPACITY = 36;
  const TEMPORAL_EVENT_TIMEBASE = 'decision-index-only';
  const RECEPTOR_CHANNELS = [
    'hook_extension',
    'hook_flexion',
    'club_motion',
    'club_vibration',
  ];
  const RECEPTOR_LABELS = {
    hook_extension: 'Hook extension',
    hook_flexion: 'Hook flexion',
    club_motion: 'Club motion',
    club_vibration: 'Club vibration',
  };
  const TEMPORAL_HISTORY_KEYS = [
    'schema',
    'source',
    'human_only',
    'capacity',
    'sample_count',
    'samples',
    'history_persistence_enabled',
    'systematic_type_mapping_exposed',
    'current_calibration_authorized',
    'stimulation_enabled',
    'runtime_transduction_enabled',
    'neural_payload_eligible',
  ].sort();
  const TEMPORAL_SAMPLE_KEYS = [
    'sequence',
    'source',
    'model',
    'encoding',
    'channels',
    'stimulation_enabled',
    'runtime_transduction_enabled',
    'systematic_type_mapping_exposed',
    'current_calibration_authorized',
    'neural_payload_eligible',
  ].sort();

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

  function exactKeys(record, expectedKeys) {
    if (!record || typeof record !== 'object' || Array.isArray(record)) return false;
    const keys = Object.keys(record).sort();
    return keys.length === expectedKeys.length
      && keys.every((key, index) => key === expectedKeys[index]);
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
        <span>RECENT RECEPTOR HISTORY</span>
        <p id="proprioceptionTemporalStatus">等待 bounded neural-handoff history…</p>
      </div>
      <div id="proprioceptionTemporalHistory" class="telemetry-lines">
        <div><span>History</span><strong>—</strong></div>
      </div>
      <div class="brain-sentence">
        <span>TEMPORAL EVENT ANALYSIS</span>
        <p id="proprioceptionTemporalAnalysisStatus">等待 decision-index event summary…</p>
      </div>
      <div id="proprioceptionTemporalAnalysis" class="telemetry-lines">
        <div><span>Analysis</span><strong>—</strong></div>
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
        <p id="proprioceptionSemanticNote">Live/history/event summary 與 SNpp39/SNpp41 候選語意分離；human diagnostics 不回流成 neural input。</p>
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

  function validateTemporalSample(sample, previousSequence) {
    if (!exactKeys(sample, TEMPORAL_SAMPLE_KEYS)) return false;
    const sequence = Number(sample.sequence);
    const channels = sample.channels;
    const keys = channels && Object.keys(channels).sort();
    const expectedKeys = [...RECEPTOR_CHANNELS].sort();
    const levelsValid = Array.isArray(keys)
      && keys.length === expectedKeys.length
      && keys.every((key, index) => key === expectedKeys[index])
      && RECEPTOR_CHANNELS.every(key => {
        const value = Number(channels[key]);
        return Number.isFinite(value) && value >= 0 && value <= 1;
      });
    const sequenceValid = Number.isInteger(sequence)
      && sequence > 0
      && (previousSequence == null || sequence === previousSequence + 1);
    return sequenceValid
      && sample.source === TEMPORAL_SOURCE
      && sample.model === 'neurofly-feco-motion-proxy-v0.1'
      && sample.encoding === 'virtual-joint-motion-only-proxy'
      && sample.stimulation_enabled === false
      && sample.runtime_transduction_enabled === false
      && sample.systematic_type_mapping_exposed === false
      && sample.current_calibration_authorized === false
      && sample.neural_payload_eligible === false
      && levelsValid;
  }

  function validateTemporalRecord(record) {
    if (!exactKeys(record, TEMPORAL_HISTORY_KEYS)) return false;
    const samples = record.samples;
    const capacity = Number(record.capacity);
    const sampleCount = Number(record.sample_count);
    let previousSequence = null;
    const samplesValid = Array.isArray(samples)
      && samples.every(sample => {
        const valid = validateTemporalSample(sample, previousSequence);
        if (valid) previousSequence = Number(sample.sequence);
        return valid;
      });
    return record.schema === TEMPORAL_SCHEMA
      && record.source === TEMPORAL_SOURCE
      && record.human_only === true
      && Number.isInteger(capacity)
      && capacity >= 1
      && capacity <= TEMPORAL_MAX_CAPACITY
      && Number.isInteger(sampleCount)
      && sampleCount === samples?.length
      && sampleCount <= capacity
      && record.history_persistence_enabled === false
      && record.systematic_type_mapping_exposed === false
      && record.current_calibration_authorized === false
      && record.stimulation_enabled === false
      && record.runtime_transduction_enabled === false
      && record.neural_payload_eligible === false
      && samplesValid;
  }

  function deriveTemporalEventAnalysis(record) {
    const samples = record.samples;
    const channels = {};

    RECEPTOR_CHANNELS.forEach(channel => {
      const events = [];
      let activeSamples = 0;
      let risingTransitions = 0;
      let fallingTransitions = 0;
      let previousActive = null;
      let current = null;

      samples.forEach((sample, index) => {
        const sequence = Number(sample.sequence);
        const level = Number(sample.channels[channel]);
        const active = level > 0;
        if (active) activeSamples += 1;

        if (active && previousActive !== true) {
          if (previousActive === false) risingTransitions += 1;
          current = {
            observed_start_sequence: sequence,
            observed_end_sequence: sequence,
            observed_duration_decisions: 1,
            peak_level: level,
            left_censored: index === 0,
            right_censored: false,
          };
          events.push(current);
        } else if (active && current) {
          current.observed_end_sequence = sequence;
          current.observed_duration_decisions = current.observed_end_sequence
            - current.observed_start_sequence
            + 1;
          current.peak_level = Math.max(current.peak_level, level);
        }

        if (!active && previousActive === true) {
          fallingTransitions += 1;
          current = null;
        }
        previousActive = active;
      });

      if (samples.length > 0 && previousActive === true && events.length > 0) {
        events[events.length - 1].right_censored = true;
      }

      channels[channel] = {
        active_sample_count: activeSamples,
        rising_transition_count_within_window: risingTransitions,
        falling_transition_count_within_window: fallingTransitions,
        event_count_observed: events.length,
        events,
      };
    });

    const firstSequence = samples.length > 0 ? Number(samples[0].sequence) : null;
    const lastSequence = samples.length > 0 ? Number(samples[samples.length - 1].sequence) : null;
    return {
      timebase: TEMPORAL_EVENT_TIMEBASE,
      sample_count: samples.length,
      first_retained_sequence: firstSequence,
      last_retained_sequence: lastSequence,
      window_left_censoring_possible: samples.length > 0 && firstSequence !== 1,
      channels,
      milliseconds_inferred: false,
      step_cycle_phase_resolved: false,
      inhibitory_lead_time_resolved: false,
    };
  }

  function renderTemporalEventAnalysis(record) {
    const analysisTarget = document.getElementById('proprioceptionTemporalAnalysis');
    if (!analysisTarget) return;
    if (!validateTemporalRecord(record)) {
      setText('proprioceptionTemporalAnalysisStatus', 'Temporal event analysis 不可用 · FAIL CLOSED');
      analysisTarget.innerHTML = '<div><span>Analysis</span><strong>—</strong></div>';
      return;
    }

    const analysis = deriveTemporalEventAnalysis(record);
    const windowLabel = analysis.sample_count === 0
      ? '尚無 retained sample'
      : `#${analysis.first_retained_sequence}–#${analysis.last_retained_sequence}`;
    const censorLabel = analysis.window_left_censoring_possible
      ? 'left-window censoring possible'
      : 'no discarded-left-window evidence';
    setText(
      'proprioceptionTemporalAnalysisStatus',
      `${analysis.timebase} · browser-local human-only derived · ms / biological phase / 9A lead time 未解析`
    );

    const rows = [
      `<div><span>Window</span><strong>${windowLabel} · ${censorLabel}</strong></div>`,
    ];
    RECEPTOR_CHANNELS.forEach(channel => {
      const summary = analysis.channels[channel];
      const latest = summary.events[summary.events.length - 1];
      let latestLabel = '無 observed event';
      if (latest) {
        const censor = [
          latest.left_censored ? 'L-censored' : null,
          latest.right_censored ? 'R-censored' : null,
        ].filter(Boolean).join(' / ');
        latestLabel = `latest #${latest.observed_start_sequence}–#${latest.observed_end_sequence}`
          + ` · ${latest.observed_duration_decisions} decisions`
          + ` · peak ${formatReceptorLevel(latest.peak_level)}`
          + (censor ? ` · ${censor}` : '');
      }
      rows.push(
        `<div><span>${RECEPTOR_LABELS[channel]}</span><strong>`
        + `${summary.event_count_observed} events · active ${summary.active_sample_count}`
        + ` · ↑ ${summary.rising_transition_count_within_window}`
        + ` · ↓ ${summary.falling_transition_count_within_window}`
        + ` · ${latestLabel}</strong></div>`
      );
    });
    analysisTarget.innerHTML = rows.join('');
  }

  function renderTemporalProprioception(view) {
    ensureProprioceptionPanel();
    const record = view?.human_diagnostics?.proprioception_temporal;
    const samples = record?.samples;
    const capacity = Number(record?.capacity);
    const sampleCount = Number(record?.sample_count);
    const valid = validateTemporalRecord(record);

    const historyTarget = document.getElementById('proprioceptionTemporalHistory');
    if (!valid || !historyTarget) {
      setText('proprioceptionTemporalStatus', 'Temporal receptor history 不可用 · FAIL CLOSED');
      if (historyTarget) historyTarget.innerHTML = '<div><span>History</span><strong>—</strong></div>';
      renderTemporalEventAnalysis(record);
      return;
    }

    setText(
      'proprioceptionTemporalStatus',
      `${sampleCount}/${capacity} 筆 verified handoff · human-only · 不寫入 checkpoint`
    );
    renderTemporalEventAnalysis(record);
    const visible = samples.slice(-8);
    if (visible.length === 0) {
      historyTarget.innerHTML = '<div><span>History</span><strong>尚無 handoff sample</strong></div>';
      return;
    }
    historyTarget.innerHTML = visible.map(sample => {
      const channels = sample.channels;
      const compact = [
        `E ${formatReceptorLevel(channels.hook_extension)}`,
        `F ${formatReceptorLevel(channels.hook_flexion)}`,
        `M ${formatReceptorLevel(channels.club_motion)}`,
        `V ${formatReceptorLevel(channels.club_vibration)}`,
      ].join(' · ');
      return `<div><span>#${sample.sequence}</span><strong>${compact}</strong></div>`;
    }).join('');
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
      'Live/history/event summary 只顯示 verified engineering receptor handoff 的 human diagnostics；A/B 仍只保留 physiology-supported inference。沒有 executable hook_extension/flexion → SNpp39/41 alias、沒有 proprioceptive current，event analysis 也不會回流成 neural input。'
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
      renderTemporalProprioception(view);
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
        renderTemporalProprioception(view);
      } catch (_) {}
    });
  } catch (_) {}
})();
// SliceDroid dashboard — wiring. All data comes from the JSON API.

import { api } from './api.js';
import { fmtNum, fmtBytes, fmtDuration, toast, tr } from './ui.js';
import { renderTimeline, renderPeers, renderCategories, categorySwatch, onThemeChange } from './charts.js';
import { Combobox } from './combobox.js';

const $ = (id) => document.getElementById(id);

const state = {
  apps: [],
  processes: [],
  mode: 'app',
  analysis: null,
};

let appCombo, procCombo;   // custom dropdowns, created in init()

/* ── health & trace info ───────────────────────────────────────── */
async function refreshHealth() {
  try {
    const h = await api.health();
    $('health-dot').className = 'health-dot ok';
    $('health-text').textContent = h.trace_loaded ? 'ready' : 'no trace loaded';
  } catch {
    $('health-dot').className = 'health-dot error';
    $('health-text').textContent = 'backend offline';
  }
}

async function refreshTraceInfo() {
  try {
    const info = await api.traceInfo();
    state.traceFile = info && info.filename ? info.filename : null;
    if (info && info.filename) {
      $('chip-trace-value').textContent = info.filename;
      $('trace-meta').hidden = false;
      $('trace-meta').textContent = `${info.filename} · ${fmtBytes(info.size)}`;
    } else {
      $('chip-trace-value').textContent = 'none';
      $('trace-meta').hidden = true;
    }
  } catch { /* health already reports connectivity */ }
}

/* ── apps ──────────────────────────────────────────────────────── */
function appItems() {
  return state.apps.map(app => ({
    value: app.package,
    label: `${app.name || app.package}${app.running ? '  ●' : ''}`,
    search: `${app.name || ''} ${app.package}`.toLowerCase(),
  }));
}

async function loadApps(refresh = false) {
  try {
    const data = refresh ? await api.refreshApps() : await api.apps();
    state.apps = data.apps || [];
    appCombo.setItems(appItems());
    $('apps-empty').hidden = state.apps.length > 0;
    if (refresh) toast(`App list refreshed — ${state.apps.length} apps`, 'success');
  } catch (err) {
    toast(`Could not load apps: ${err.message}`, 'error');
  }
}

/* ── processes from the loaded trace (PID picker) ──────────────── */
function procItems() {
  return state.processes.map(proc => ({
    value: String(proc.tgid),
    label: `${proc.name}  ·  pid ${proc.tgid}  ·  ${proc.events} ev`,
    search: `${proc.name} ${proc.tgid}`.toLowerCase(),
  }));
}

async function loadTraceProcesses() {
  try {
    const data = await api.traceProcesses();
    state.processes = data.processes || [];
  } catch {
    state.processes = [];
  }
  procCombo.setItems(procItems());
  $('proc-empty').hidden = state.processes.length > 0;
  // When there is no device app mapping but the trace has processes, land the
  // user on the PID picker so the target selection is never a dead end.
  if (state.processes.length > 0 && state.apps.length === 0) setMode('pid');
}

/* ── upload ────────────────────────────────────────────────────── */
function wireUpload() {
  const dz = $('dropzone');
  const input = $('trace-file-input');

  const pick = () => input.click();
  dz.addEventListener('click', pick);
  dz.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); pick(); } });

  dz.addEventListener('dragover', (e) => { e.preventDefault(); dz.classList.add('dragover'); });
  dz.addEventListener('dragleave', () => dz.classList.remove('dragover'));
  dz.addEventListener('drop', (e) => {
    e.preventDefault();
    dz.classList.remove('dragover');
    if (e.dataTransfer.files.length) uploadFile(e.dataTransfer.files[0]);
  });
  input.addEventListener('change', () => { if (input.files.length) uploadFile(input.files[0]); });
}

async function uploadFile(file) {
  $('trace-meta').hidden = false;
  $('trace-meta').textContent = `Uploading ${file.name}…`;
  try {
    const info = await api.upload(file);
    // A new trace invalidates whatever is on screen — reset to a clean state so
    // stale results from the previous trace are never mistaken for the new one.
    clearResults(`Trace loaded: ${info.filename}. Pick a target below and run Analyze.`);
    procCombo.clear();
    $('pid-input').value = '';
    await refreshTraceInfo();
    await refreshHealth();
    await loadTraceProcesses();
    toast(`Trace loaded: ${info.filename} — choose a target and Analyze`, 'success');
  } catch (err) {
    $('trace-meta').hidden = true;
    toast(`Upload failed: ${err.message}`, 'error');
  }
}

/* Return the results area to the empty state (new trace, or no analysis yet). */
function clearResults(message) {
  state.analysis = null;
  $('results-content').hidden = true;
  $('results-content').classList.remove('reveal');
  $('empty-state').hidden = false;
  $('export-block').hidden = true;
  $('chip-target').hidden = true;
  $('footer-generated').textContent = '';
  if (message) {
    $('empty-title').textContent = 'Ready to analyze';
    $('empty-message').textContent = message;
  }
}

/* ── analyze ───────────────────────────────────────────────────── */
function analyzePayload() {
  const windowSize = parseInt($('window-size').value, 10) || 500;
  const overlap = parseInt($('overlap').value, 10) || 0;
  if (state.mode === 'pid') {
    // A manually typed PID wins; otherwise use the selected trace process.
    const typed = parseInt($('pid-input').value, 10);
    const selected = parseInt(procCombo.value, 10);
    const pid = typed || selected;
    if (!pid) return { error: 'Pick a process from the trace or enter a PID.' };
    return { mode: 'pid', pid, window_size: windowSize, overlap };
  }
  const pkg = appCombo.value;
  if (!pkg) return { error: 'Select a target application first.' };
  return { mode: 'app', package: pkg, window_size: windowSize, overlap };
}

async function runAnalysis() {
  const payload = analyzePayload();
  if (payload.error) { toast(payload.error, 'error'); return; }

  const btn = $('analyze-btn');
  btn.disabled = true;
  $('analyze-spinner').hidden = false;
  $('analyze-status').textContent = 'Parsing trace and slicing — large traces can take a while…';

  try {
    const result = await api.analyze(payload);
    state.analysis = result;
    render(result);
    toast('Analysis complete', 'success');
  } catch (err) {
    toast(`Analysis failed: ${err.message}`, 'error', 8000);
  } finally {
    btn.disabled = false;
    $('analyze-spinner').hidden = true;
    $('analyze-status').textContent = '';
  }
}

/* ── rendering ─────────────────────────────────────────────────── */
function render(result) {
  $('empty-state').hidden = true;
  const content = $('results-content');
  content.hidden = false;
  content.classList.remove('reveal');
  void content.offsetWidth;          // restart the stagger animation
  content.classList.add('reveal');
  $('export-block').hidden = false;

  const { meta, summary, timeline, network, sensitive, insights } = result;

  // target chip
  $('chip-target').hidden = false;
  $('chip-target-value').textContent =
    meta.target.mode === 'app'
      ? (meta.target.name || meta.target.package)
      : `pid ${meta.target.pids.join(', ')}`;

  // tiles
  $('tile-events').textContent = fmtNum(meta.total_events);
  $('tile-duration').textContent = fmtDuration(meta.duration_s);
  $('tile-sliced').textContent = fmtNum(meta.sliced_events);
  $('tile-windows').textContent = fmtNum(meta.windows);
  $('tile-peers').textContent = fmtNum(network.metrics.unique_tcp_peers + network.metrics.unique_udp_peers);
  $('tile-bytes-out').textContent = fmtBytes(network.metrics.tcp_bytes_sent + network.metrics.udp_bytes_sent);

  // charts
  renderTimeline('timeline-chart', timeline);
  renderPeers('peers-chart', network.peers || []);
  renderCategories('categories-chart', summary.event_categories);

  // network metric chips
  const m = network.metrics;
  const chips = [
    ['TCP conns', fmtNum(m.tcp_connections)],
    ['UDP flows', fmtNum(m.udp_connections)],
    ['TCP sent', fmtBytes(m.tcp_bytes_sent)],
    ['TCP received', fmtBytes(m.tcp_bytes_received)],
    ['UDP sent', fmtBytes(m.udp_bytes_sent)],
    ['UDP received', fmtBytes(m.udp_bytes_received)],
  ];
  const host = $('net-metrics');
  host.innerHTML = '';
  for (const [label, value] of chips) {
    const chip = document.createElement('span');
    chip.className = 'net-chip';
    const b = document.createElement('b');
    b.textContent = value;
    chip.append(`${label} `, b);
    host.appendChild(chip);
  }

  // peers table
  const peersBody = $('peers-tbody');
  peersBody.innerHTML = '';
  for (const p of network.peers || []) {
    peersBody.appendChild(tr([
      p.ip, p.protocol, (p.ports || []).join(', '),
      { text: fmtNum(p.connections), num: true },
      { text: fmtBytes(p.bytes_sent), num: true },
      { text: fmtBytes(p.bytes_received), num: true },
    ]));
  }

  // connections table
  const connBody = $('connections-tbody');
  connBody.innerHTML = '';
  for (const c of network.connections || []) {
    connBody.appendChild(tr([
      c.protocol,
      `${c.src}:${c.sport}`,
      `${c.dst}:${c.dport}`,
      { text: fmtBytes(c.bytes_sent), num: true },
      { text: fmtBytes(c.bytes_received), num: true },
      { text: (c.last_ts - c.first_ts).toFixed(2), num: true },
    ]));
  }

  // sensitive table
  const sensBody = $('sensitive-tbody');
  sensBody.innerHTML = '';
  $('sensitive-empty').hidden = sensitive.length > 0;
  $('sensitive-wrap').hidden = sensitive.length === 0;
  for (const s of sensitive) {
    const badge = document.createElement('span');
    badge.className = 'cat-badge';
    const dot = document.createElement('span');
    dot.className = 'dot';
    dot.style.background = categorySwatch(s.category);
    badge.append(dot, s.category);
    sensBody.appendChild(tr([
      badge, s.process,
      { text: String(s.window), num: true },
      s.pathname || s.identifier,
    ]));
  }

  // insights
  const list = $('insights-list');
  list.innerHTML = '';
  for (const i of insights || []) {
    const li = document.createElement('li');
    if (i.level === 'warning') li.classList.add('warning');
    const marker = document.createElement('span');
    marker.className = 'marker';
    li.append(marker, i.text);
    list.appendChild(li);
  }
  if (!insights || insights.length === 0) {
    const li = document.createElement('li');
    li.textContent = 'No notable findings for this slice.';
    list.appendChild(li);
  }

  $('footer-generated').textContent = meta.generated_at ? `analysis ${meta.generated_at}` : '';
}

/* ── mode & tabs ───────────────────────────────────────────────── */
function wireControls() {
  $('mode-app').addEventListener('click', () => setMode('app'));
  $('mode-pid').addEventListener('click', () => setMode('pid'));
  $('apps-refresh').addEventListener('click', () => loadApps(true));
  $('analyze-btn').addEventListener('click', runAnalysis);

  $('tab-peers').addEventListener('click', () => setTab('peers'));
  $('tab-connections').addEventListener('click', () => setTab('connections'));
}

function setMode(mode) {
  state.mode = mode;
  $('mode-app').classList.toggle('active', mode === 'app');
  $('mode-pid').classList.toggle('active', mode === 'pid');
  $('mode-app').setAttribute('aria-selected', mode === 'app');
  $('mode-pid').setAttribute('aria-selected', mode === 'pid');
  $('target-app-controls').hidden = mode !== 'app';
  $('target-pid-controls').hidden = mode !== 'pid';
}

function setTab(tab) {
  $('tab-peers').classList.toggle('active', tab === 'peers');
  $('tab-connections').classList.toggle('active', tab === 'connections');
  $('tab-peers').setAttribute('aria-selected', tab === 'peers');
  $('tab-connections').setAttribute('aria-selected', tab === 'connections');
  $('table-peers').hidden = tab !== 'peers';
  $('table-connections').hidden = tab !== 'connections';
}

/* ── boot ──────────────────────────────────────────────────────── */
async function init() {
  appCombo = new Combobox($('app-combo'), {
    placeholder: 'Search apps…',
    emptyText: 'No apps — run setup or use PID',
  });
  procCombo = new Combobox($('proc-combo'), {
    placeholder: 'Search processes…',
    emptyText: 'Upload a trace to list its processes',
    // Selecting a trace process clears any stale manual PID entry.
    onChange: () => { $('pid-input').value = ''; },
  });

  wireUpload();
  wireControls();
  // Only chart colors are theme-derived — rebuild charts, leave the DOM alone.
  onThemeChange(() => {
    if (!state.analysis) return;
    renderTimeline('timeline-chart', state.analysis.timeline);
    renderPeers('peers-chart', state.analysis.network.peers || []);
    renderCategories('categories-chart', state.analysis.summary.event_categories);
  });

  await refreshHealth();
  refreshTraceInfo();
  await loadApps();          // must resolve before the PID auto-switch decision
  await loadTraceProcesses();

  // Restore the last analysis only if it belongs to the currently loaded trace,
  // so a leftover analysis from a different trace never shows as if it were this
  // one's.
  try {
    const last = await api.analysis();
    if (last && last.meta) {
      const analysedTrace = (last.meta.trace_file || '').split('/').pop();
      if (!state.traceFile || analysedTrace === state.traceFile) {
        state.analysis = last;
        render(last);
      }
    }
  } catch { /* no previous analysis — keep the empty state */ }
}

init();

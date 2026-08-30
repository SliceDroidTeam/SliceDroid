// Chart rendering for the SliceDroid dashboard (Chart.js v4, loaded globally).
// Colors are read from CSS custom properties so light/dark stay in sync.

const charts = {};   // id -> Chart instance

function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function tokens() {
  return {
    ink: cssVar('--ink'),
    ink2: cssVar('--ink-2'),
    muted: cssVar('--ink-muted'),
    hairline: cssVar('--hairline'),
    surface: cssVar('--surface'),
    accent: cssVar('--accent'),
    critical: cssVar('--critical'),
    mono: cssVar('--font-mono'),
  };
}

// Fixed category -> color-slot assignment (never reordered, never cycled).
const CATEGORY_SLOTS = {
  tcp: '--s1-tcp',
  udp: '--s2-udp',
  camera: '--s3',
  audio_in: '--s4',
  gnss: '--s5',
  bluetooth: '--s6',
  contacts: '--s7',
  sms: '--s8',
};

function categoryColor(category) {
  return cssVar(CATEGORY_SLOTS[category] || '--s-other');
}

function destroy(id) {
  if (charts[id]) { charts[id].destroy(); delete charts[id]; }
}

function baseScaleOpts(t) {
  return {
    grid: { color: t.hairline, drawTicks: false },
    border: { color: t.hairline },
    ticks: { color: t.muted, font: { family: t.mono, size: 11 } },
  };
}

/* ── Behavior timeline: the instrument strip ─────────────────────
   One lane per device category, plus TCP and UDP lanes. Bubble size
   encodes events per window. Sensitive accesses project a vertical
   hairline across all lanes — the alignment of a PII read with a
   network burst is exactly what the analyst is looking for.        */
export function renderTimeline(canvasId, timeline) {
  destroy(canvasId);
  const t = tokens();

  const laneNames = [...timeline.categories.filter(c => c !== 'tcp' && c !== 'udp'), 'tcp', 'udp'];
  const laneIndex = new Map(laneNames.map((name, i) => [name, i]));

  const datasets = timeline.series
    .filter(s => laneIndex.has(s.category))
    .map(s => ({
      label: s.category,
      data: s.points.map(([w, count]) => ({
        x: w, y: laneIndex.get(s.category),
        r: Math.min(3 + 2.2 * Math.log2(count + 1), 13),
        count,
      })),
      backgroundColor: categoryColor(s.category) + 'CC',
      borderColor: categoryColor(s.category),
      borderWidth: 1,
    }));

  for (const proto of ['tcp', 'udp']) {
    const points = (timeline.network || [])
      .filter(n => n[proto] > 0)
      .map(n => ({
        x: n.window, y: laneIndex.get(proto),
        r: Math.min(3 + 2.2 * Math.log2(n[proto] + 1), 13),
        count: n[proto],
      }));
    datasets.push({
      label: proto,
      data: points,
      backgroundColor: categoryColor(proto) + 'CC',
      borderColor: categoryColor(proto),
      borderWidth: 1,
    });
  }

  // Sensitive accesses: ringed diamonds on their own lane.
  const sensitive = (timeline.sensitive || []).filter(s => laneIndex.has(s.category));
  datasets.push({
    label: 'sensitive access',
    data: sensitive.map(s => ({
      x: s.window, y: laneIndex.get(s.category), r: 7,
      count: 1, identifier: s.identifier, pathname: s.pathname,
    })),
    pointStyle: 'rectRot',
    backgroundColor: t.critical,
    borderColor: t.surface,
    borderWidth: 2,
  });

  const sensitiveWindows = [...new Set((timeline.sensitive || []).map(s => s.window))];

  const lanePlugin = {
    id: 'laneBands',
    beforeDatasetsDraw(chart) {
      const { ctx, chartArea, scales } = chart;
      if (!chartArea) return;
      ctx.save();
      // alternating lane bands
      for (let i = 0; i < laneNames.length; i += 2) {
        const y0 = scales.y.getPixelForValue(i - 0.5);
        const y1 = scales.y.getPixelForValue(i + 0.5);
        ctx.fillStyle = t.hairline + '55';
        ctx.fillRect(chartArea.left, Math.min(y0, y1), chartArea.right - chartArea.left, Math.abs(y1 - y0));
      }
      // sensitive hairlines across all lanes
      ctx.strokeStyle = t.critical + '59';
      ctx.lineWidth = 1;
      for (const w of sensitiveWindows) {
        const x = scales.x.getPixelForValue(w);
        if (x < chartArea.left || x > chartArea.right) continue;
        ctx.beginPath();
        ctx.moveTo(x, chartArea.top);
        ctx.lineTo(x, chartArea.bottom);
        ctx.stroke();
      }
      ctx.restore();
    },
  };

  charts[canvasId] = new Chart(document.getElementById(canvasId), {
    type: 'bubble',
    data: { datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: matchMedia('(prefers-reduced-motion: reduce)').matches ? false : { duration: 300 },
      scales: {
        x: {
          ...baseScaleOpts(t),
          title: { display: true, text: 'analysis window', color: t.muted, font: { size: 11 } },
          beginAtZero: true,
          ticks: { ...baseScaleOpts(t).ticks, precision: 0 },
        },
        y: {
          ...baseScaleOpts(t),
          reverse: true,
          min: -0.6,
          max: laneNames.length - 0.4,
          grid: { display: false },
          ticks: {
            ...baseScaleOpts(t).ticks,
            stepSize: 1,
            autoSkip: false,
            callback: (v) => Number.isInteger(v) ? (laneNames[v] ?? '') : '',
          },
        },
      },
      plugins: {
        legend: { display: false },   // lane labels on the axis carry identity
        tooltip: {
          titleFont: { family: t.mono },
          bodyFont: { family: t.mono },
          callbacks: {
            title: (items) => `window ${items[0].raw.x}`,
            label: (item) => {
              const raw = item.raw;
              if (item.dataset.label === 'sensitive access') {
                return ` ${laneNames[raw.y]} — sensitive read (${raw.pathname || raw.identifier})`;
              }
              return ` ${item.dataset.label}: ${raw.count} event${raw.count === 1 ? '' : 's'}`;
            },
          },
        },
      },
    },
    plugins: [lanePlugin],
  });
}

/* ── Top peers by total bytes (single measure -> single hue) ───── */
export function renderPeers(canvasId, peers) {
  destroy(canvasId);
  const t = tokens();

  const top = [...peers]
    .map(p => ({ ...p, total: (p.bytes_sent || 0) + (p.bytes_received || 0) }))
    .sort((a, b) => b.total - a.total)
    .slice(0, 10);

  charts[canvasId] = new Chart(document.getElementById(canvasId), {
    type: 'bar',
    data: {
      labels: top.map(p => `${p.ip} (${p.protocol})`),
      datasets: [{
        data: top.map(p => p.total),
        backgroundColor: t.accent,
        borderRadius: 4,
        maxBarThickness: 18,
      }],
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      animation: matchMedia('(prefers-reduced-motion: reduce)').matches ? false : { duration: 300 },
      scales: {
        x: {
          ...baseScaleOpts(t),
          title: { display: true, text: 'bytes transferred', color: t.muted, font: { size: 11 } },
        },
        y: { ...baseScaleOpts(t), grid: { display: false } },
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          bodyFont: { family: t.mono },
          callbacks: {
            label: (item) => {
              const p = top[item.dataIndex];
              return [` total: ${item.formattedValue} B`,
                      ` sent: ${p.bytes_sent} B · received: ${p.bytes_received} B`,
                      ` connections: ${p.connections}`];
            },
          },
        },
      },
    },
  });
}

/* ── Event mix (single measure -> single hue) ──────────────────── */
export function renderCategories(canvasId, eventCategories) {
  destroy(canvasId);
  const t = tokens();

  const entries = Object.entries(eventCategories || {}).sort((a, b) => b[1] - a[1]);

  charts[canvasId] = new Chart(document.getElementById(canvasId), {
    type: 'bar',
    data: {
      labels: entries.map(([k]) => k),
      datasets: [{
        data: entries.map(([, v]) => v),
        backgroundColor: t.accent,
        borderRadius: 4,
        maxBarThickness: 16,
      }],
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      animation: matchMedia('(prefers-reduced-motion: reduce)').matches ? false : { duration: 300 },
      scales: {
        x: { ...baseScaleOpts(t), ticks: { ...baseScaleOpts(t).ticks, precision: 0 } },
        y: { ...baseScaleOpts(t), grid: { display: false } },
      },
      plugins: { legend: { display: false } },
    },
  });
}

export function categorySwatch(category) {
  return categoryColor(category);
}

// Re-render all charts when the OS theme flips (colors are theme-derived).
export function onThemeChange(rerender) {
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', rerender);
}

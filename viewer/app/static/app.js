/* Simple Grafana-like viewer using Plotly */
const api = {
  async listSeries(hours) {
    const url = new URL('/api/series', window.location.origin);
    url.searchParams.set('hours', hours);
    const res = await fetch(url);
    return res.json();
  },
  async getData(keys, startMs, endMs) {
    const url = new URL('/api/data', window.location.origin);
    for (const k of keys) url.searchParams.append('keys', k);
    url.searchParams.set('start_ms', startMs);
    url.searchParams.set('end_ms', endMs);
    const res = await fetch(url);
    return res.json();
  }
};

const ui = {
  seriesDiv: document.getElementById('series'),
  chart: document.getElementById('chart'),
  rangeButtons: document.querySelectorAll('button[data-range]'),
};

let selectedHours = 24;
let selectedKeys = new Set();

function nowMs() { return Date.now(); }
function msAgo(h) { return nowMs() - h * 3600 * 1000; }

async function refreshSeries() {
  const keys = await api.listSeries(selectedHours);
  ui.seriesDiv.innerHTML = '';
  for (const k of keys) {
    const id = `chk_${k}`;
    const div = document.createElement('div');
    div.className = 'series-item';
    const input = document.createElement('input');
    input.type = 'checkbox';
    input.id = id;
    input.checked = selectedKeys.size === 0 || selectedKeys.has(k);
    const label = document.createElement('label');
    label.htmlFor = id;
    label.textContent = k;
    input.addEventListener('change', () => {
      if (input.checked) selectedKeys.add(k); else selectedKeys.delete(k);
      draw();
    });
    div.appendChild(input);
    div.appendChild(label);
    ui.seriesDiv.appendChild(div);
  }
}

async function draw() {
  const end = nowMs();
  const start = msAgo(selectedHours);

  // Determine which keys to fetch
  let keysToFetch = [];
  const checkboxes = ui.seriesDiv.querySelectorAll('input[type="checkbox"]');
  checkboxes.forEach(cb => { if (cb.checked) keysToFetch.push(cb.nextSibling.textContent); });

  if (keysToFetch.length === 0) {
    Plotly.newPlot(ui.chart, [], {title: 'Ingen serie vald'});
    return;
  }

  const data = await api.getData(keysToFetch, start, end);
  const traces = [];
  for (const [k, rows] of Object.entries(data)) {
    const xs = rows.map(r => new Date(r.ts));
    const ys = rows.map(r => r.v);
    traces.push({
      name: k,
      x: xs,
      y: ys,
      mode: 'lines',
      type: 'scattergl',
    });
  }

  const layout = {
    margin: {l: 40, r: 20, t: 20, b: 40},
    xaxis: {type: 'date', rangeselector: {buttons: []}},
    yaxis: {fixedrange: false},
    showlegend: true,
  };
  Plotly.newPlot(ui.chart, traces, layout, {responsive: true});
}

async function init() {
  ui.rangeButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      selectedHours = parseInt(btn.dataset.range, 10);
      refreshSeries().then(draw);
    });
  });

  await refreshSeries();
  await draw();

  // Auto-refresh every 10s
  setInterval(draw, 10000);
}

init();

from nautobot.apps.jobs import Job, register_jobs


class LiveDashboardGenerator(Job):
    class Meta:
        name = "6. Live Dashboard Generator"
        description = "Generates a live auto-refreshing dashboard via REST API"
        has_sensitive_variables = False

    def run(self):
        html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Link3 Live Network Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: Arial, sans-serif; background: #F0F4F8; color: #1F4E79; }
  .header { background: #1F4E79; color: white; padding: 20px 40px;
            display: flex; justify-content: space-between; align-items: center; }
  .header h1 { font-size: 22px; }
  .live-badge { background: #00B050; color: white; padding: 6px 14px;
                border-radius: 20px; font-size: 13px; font-weight: bold; }
  .last-updated { font-size: 12px; opacity: 0.8; margin-top: 4px; }
  .config-bar { background: #2E75B6; padding: 12px 40px; display: flex;
                align-items: center; gap: 16px; }
  .config-bar label { color: white; font-size: 13px; }
  .config-bar input { padding: 6px 10px; border-radius: 4px; border: none;
                      font-size: 13px; width: 320px; }
  .config-bar button { background: #00B050; color: white; border: none;
                       padding: 7px 18px; border-radius: 4px; cursor: pointer;
                       font-size: 13px; font-weight: bold; }
  .kpi-row { display: flex; gap: 16px; padding: 24px 40px 0; }
  .kpi { background: white; border-radius: 8px; padding: 20px 24px; flex: 1;
         box-shadow: 0 2px 8px rgba(0,0,0,0.08); border-top: 4px solid #2E75B6;
         text-align: center; }
  .kpi h2 { font-size: 40px; color: #1F4E79; }
  .kpi p { font-size: 13px; color: #595959; margin-top: 4px; }
  .charts { display: grid; grid-template-columns: 1fr 1fr; gap: 24px;
            padding: 24px 40px; }
  .chart-box { background: white; border-radius: 8px; padding: 24px;
               box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
  .chart-box h3 { font-size: 14px; color: #1F4E79; margin-bottom: 16px;
                  border-bottom: 2px solid #EBF3FB; padding-bottom: 8px; }
  .chart-wide { grid-column: span 2; }
  .csv-btn { background: #1F4E79; color: white; border: none; padding: 8px 18px;
             border-radius: 4px; cursor: pointer; font-size: 12px; float: right;
             margin-top: -32px; }
  .csv-btn:hover { background: #2E75B6; }
  .error-msg { background: #FCE4D6; color: #843C0C; padding: 12px 40px;
               font-size: 13px; display: none; }
  .footer { text-align: center; padding: 20px; font-size: 12px; color: #595959; }
  .loading { text-align: center; padding: 40px; color: #2E75B6; font-size: 16px; }
</style>
</head>
<body>

<div class="header">
  <div>
    <h1>📊 Link3 Live Network Dashboard</h1>
    <div class="last-updated">Last updated: <span id="lastUpdated">Loading...</span></div>
  </div>
  <div class="live-badge">🟢 LIVE — Auto-refresh: 30s</div>
</div>

<div class="config-bar">
  <label>Nautobot URL + API Token:</label>
  <input type="text" id="apiUrl" placeholder="http://203.76.101.214:8080" value="http://203.76.101.214:8080"/>
  <input type="text" id="apiToken" placeholder="Paste your Nautobot API token here" style="width:360px"/>
  <button onclick="startDashboard()">▶ Connect</button>
</div>

<div class="error-msg" id="errorMsg"></div>

<div class="kpi-row">
  <div class="kpi"><h2 id="kpiDevices">—</h2><p>Total Devices</p></div>
  <div class="kpi"><h2 id="kpiActive">—</h2><p>Active Devices</p></div>
  <div class="kpi"><h2 id="kpiCircuits">—</h2><p>Total Circuits</p></div>
  <div class="kpi"><h2 id="kpiPrefixes">—</h2><p>IP Prefixes</p></div>
</div>

<div class="charts">
  <div class="chart-box">
    <h3>🖥️ Devices by Role</h3>
    <button class="csv-btn" onclick="downloadCSV('role')">⬇ CSV</button>
    <canvas id="roleChart"></canvas>
  </div>
  <div class="chart-box">
    <h3>🔌 Circuit Status</h3>
    <button class="csv-btn" onclick="downloadCSV('circuit')">⬇ CSV</button>
    <canvas id="circuitChart"></canvas>
  </div>
  <div class="chart-box chart-wide">
    <h3>📍 Top 10 Locations by Device Count</h3>
    <button class="csv-btn" onclick="downloadCSV('location')">⬇ CSV</button>
    <canvas id="locationChart"></canvas>
  </div>
  <div class="chart-box">
    <h3>🌐 IP Utilization Buckets</h3>
    <button class="csv-btn" onclick="downloadCSV('ip')">⬇ CSV</button>
    <canvas id="ipChart"></canvas>
  </div>
  <div class="chart-box">
    <h3>📡 BTS Health</h3>
    <button class="csv-btn" onclick="downloadCSV('bts')">⬇ CSV</button>
    <canvas id="btsChart"></canvas>
  </div>
  <div class="chart-box chart-wide">
    <h3>📋 All Devices by Status</h3>
    <button class="csv-btn" onclick="downloadCSV('status')">⬇ CSV</button>
    <canvas id="statusChart"></canvas>
  </div>
</div>

<div class="footer">
  Link3 Technologies Ltd. — Technology Department | Confidential — Internal Use Only
</div>

<script>
const COLORS = ['#1F4E79','#2E75B6','#00B0F0','#375623','#843C0C',
                '#70AD47','#ED7D31','#FFC000','#4472C4','#A9D18E'];

let charts = {};
let chartData = {};
let refreshTimer = null;

function getHeaders() {
  return {
    'Authorization': 'Token ' + document.getElementById('apiToken').value.trim(),
    'Content-Type': 'application/json'
  };
}

function getBase() {
  return document.getElementById('apiUrl').value.trim().replace(/\\/$/, '');
}

async function fetchAll(endpoint) {
  const base = getBase();
  let results = [];
  let url = `${base}/api/${endpoint}/?limit=1000&format=json`;
  while (url) {
    const res = await fetch(url, { headers: getHeaders() });
    if (!res.ok) throw new Error(`API error: ${res.status} on ${endpoint}`);
    const data = await res.json();
    results = results.concat(data.results);
    url = data.next;
  }
  return results;
}

function showError(msg) {
  const el = document.getElementById('errorMsg');
  el.style.display = 'block';
  el.textContent = '⚠️ ' + msg;
}

function hideError() {
  document.getElementById('errorMsg').style.display = 'none';
}

function makeOrUpdate(id, type, labels, data, bgColors, label='Count') {
  chartData[id] = { labels, data };
  if (charts[id]) {
    charts[id].data.labels = labels;
    charts[id].data.datasets[0].data = data;
    charts[id].update();
  } else {
    const ctx = document.getElementById(id).getContext('2d');
    charts[id] = new Chart(ctx, {
      type,
      data: {
        labels,
        datasets: [{ label, data, backgroundColor: bgColors,
                     borderColor: type === 'bar' ? bgColors : undefined,
                     borderWidth: type === 'bar' ? 1 : 0 }]
      },
      options: {
        responsive: true,
        plugins: { legend: { position: ['pie','doughnut'].includes(type) ? 'right' : 'top',
                             display: true } },
        scales: type === 'bar' ? { y: { beginAtZero: true } } : {}
      }
    });
  }
}

async function refreshData() {
  hideError();
  try {
    const [devices, circuits, prefixes] = await Promise.all([
      fetchAll('dcim/devices'),
      fetchAll('circuits/circuits'),
      fetchAll('ipam/prefixes')
    ]);

    // KPIs
    document.getElementById('kpiDevices').textContent = devices.length;
    document.getElementById('kpiActive').textContent =
      devices.filter(d => d.status?.value === 'active').length;
    document.getElementById('kpiCircuits').textContent = circuits.length;
    document.getElementById('kpiPrefixes').textContent = prefixes.length;

    // Chart 1 — Devices by Role
    const roleMap = {};
    devices.filter(d => d.status?.value === 'active').forEach(d => {
      const r = d.role?.name || 'Unknown';
      roleMap[r] = (roleMap[r] || 0) + 1;
    });
    makeOrUpdate('roleChart', 'doughnut',
      Object.keys(roleMap), Object.values(roleMap), COLORS);

    // Chart 2 — Circuit Status
    const circuitMap = {};
    circuits.forEach(c => {
      const s = c.status?.label || 'Unknown';
      circuitMap[s] = (circuitMap[s] || 0) + 1;
    });
    makeOrUpdate('circuitChart', 'pie',
      Object.keys(circuitMap), Object.values(circuitMap), COLORS);

    // Chart 3 — Top 10 Locations
    const locMap = {};
    devices.filter(d => d.status?.value === 'active').forEach(d => {
      const l = d.location?.name || 'Unknown';
      locMap[l] = (locMap[l] || 0) + 1;
    });
    const top10 = Object.entries(locMap).sort((a,b) => b[1]-a[1]).slice(0,10);
    makeOrUpdate('locationChart', 'bar',
      top10.map(x=>x[0]), top10.map(x=>x[1]),
      Array(10).fill('#2E75B6'), 'Devices');

    // Chart 4 — IP Utilization (approximate from prefix data)
    let low=0, med=0, high=0, crit=0;
    prefixes.forEach(p => {
      const pct = p.utilization || 0;
      if (pct < 25) low++;
      else if (pct < 50) med++;
      else if (pct < 80) high++;
      else crit++;
    });
    makeOrUpdate('ipChart', 'bar',
      ['Low (0-24%)', 'Medium (25-49%)', 'High (50-79%)', 'Critical (80%+)'],
      [low, med, high, crit],
      ['#70AD47','#FFC000','#ED7D31','#FF0000'], 'Prefixes');

    // Chart 5 — BTS Health
    const btsAll = devices.filter(d =>
      d.role?.name?.toLowerCase().includes('bts'));
    const btsActive = btsAll.filter(d => d.status?.value === 'active').length;
    const btsInactive = btsAll.length - btsActive;
    makeOrUpdate('btsChart', 'doughnut',
      ['Active', 'Inactive'], [btsActive, btsInactive],
      ['#375623','#843C0C']);

    // Chart 6 — All Devices by Status
    const statusMap = {};
    devices.forEach(d => {
      const s = d.status?.label || 'Unknown';
      statusMap[s] = (statusMap[s] || 0) + 1;
    });
    makeOrUpdate('statusChart', 'bar',
      Object.keys(statusMap), Object.values(statusMap),
      COLORS, 'Devices');

    document.getElementById('lastUpdated').textContent = new Date().toLocaleTimeString();

  } catch(err) {
    showError(err.message + ' — Check your URL and API token.');
  }
}

function downloadCSV(chartId) {
  const d = chartData[chartId + 'Chart'];
  if (!d) return;
  let csv = 'Label,Count\\n';
  d.labels.forEach((l, i) => { csv += `"${l}",${d.data[i]}\\n`; });
  const blob = new Blob([csv], { type: 'text/csv' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `link3_${chartId}_report.csv`;
  a.click();
}

function startDashboard() {
  if (!document.getElementById('apiToken').value.trim()) {
    showError('Please enter your API token first!');
    return;
  }
  if (refreshTimer) clearInterval(refreshTimer);
  refreshData();
  refreshTimer = setInterval(refreshData, 30000);
}
</script>
</body></html>"""

        self.create_file("link3_live_dashboard.html", html)
        self.logger.info(
            "Live dashboard generated! Download the file, open in Chrome, "
            "enter your Nautobot URL and API token, then click Connect."
        )


register_jobs(LiveDashboardGenerator)

from nautobot.apps.jobs import Job, register_jobs
from nautobot.dcim.models import Location, Device

HTML_STYLE = """
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: Arial, sans-serif; background: #F0F4F8; color: #1F4E79; }
  .header { background: #1F4E79; color: white; padding: 20px 40px; }
  .header h1 { font-size: 24px; }
  .header p { font-size: 13px; opacity: 0.8; margin-top: 4px; }
  .filters { background: white; padding: 16px 40px; border-bottom: 2px solid #EBF3FB;
             display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
  .filters label { font-size: 13px; font-weight: bold; color: #1F4E79; }
  .filters select, .filters input { padding: 7px 10px; border: 1px solid #AABBD4;
    border-radius: 4px; font-size: 13px; }
  .filters button { padding: 7px 16px; border: none; border-radius: 4px;
    cursor: pointer; font-size: 13px; font-weight: bold; }
  .btn-filter { background: #2E75B6; color: white; }
  .btn-reset { background: #F2F2F2; color: #595959; }
  .btn-csv { background: #375623; color: white; }
  .btn-pdf { background: #843C0C; color: white; }
  .kpi-row { display: flex; gap: 16px; padding: 20px 40px 0; }
  .kpi { background: white; border-radius: 8px; padding: 16px 20px; flex: 1;
         box-shadow: 0 2px 8px rgba(0,0,0,0.08); border-top: 4px solid #2E75B6;
         text-align: center; }
  .kpi h2 { font-size: 36px; color: #1F4E79; }
  .kpi p { font-size: 12px; color: #595959; margin-top: 4px; }
  .content { padding: 20px 40px; }
  table { width: 100%; border-collapse: collapse; background: white;
          border-radius: 8px; overflow: hidden;
          box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
  th { background: #1F4E79; color: white; padding: 10px 12px;
       text-align: left; font-size: 13px; }
  td { padding: 9px 12px; border-bottom: 1px solid #EBF3FB; font-size: 13px; }
  tr:hover { background: #F0F4F8; }
  .bar-wrap { background: #EBF3FB; border-radius: 4px; height: 14px;
              width: 100%; min-width: 80px; }
  .bar-fill { background: #2E75B6; border-radius: 4px; height: 14px; }
  .chart-box { background: white; border-radius: 8px; padding: 24px;
               box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 24px; }
  .chart-box h3 { font-size: 14px; color: #1F4E79; margin-bottom: 16px;
                  border-bottom: 2px solid #EBF3FB; padding-bottom: 8px; }
  .footer { text-align: center; padding: 20px; font-size: 12px; color: #595959; }
  @media print {
    .filters { display: none !important; }
    body { background: white; }
  }
</style>
"""

class LocationInventoryReport(Job):
    class Meta:
        name = "9. Location Inventory Report"
        description = "All locations with device counts, hierarchy, and charts — filterable, CSV & PDF"
        has_sensitive_variables = False

    def run(self):
        locations = Location.objects.all().order_by("location_type__name", "name")

        rows_data = []
        loc_types = set()
        parents = set()
        max_devices = 0

        for loc in locations:
            loc_type = loc.location_type.name if loc.location_type else "Unknown"
            parent = loc.parent.name if loc.parent else "—"
            device_count = Device.objects.filter(location=loc).count()
            status = loc.status.name if loc.status else "Active"

            loc_types.add(loc_type)
            if parent != "—":
                parents.add(parent)
            if device_count > max_devices:
                max_devices = device_count

            rows_data.append({
                "name": loc.name,
                "type": loc_type,
                "parent": parent,
                "status": status,
                "devices": device_count,
            })

        type_opts = "".join(f'<option value="{t}">{t}</option>' for t in sorted(loc_types))

        rows_js = str(rows_data).replace("'", '"').replace('True','true').replace('False','false').replace('None','null')

        # Chart data — devices by location type
        type_counts = {}
        for r in rows_data:
            type_counts[r["type"]] = type_counts.get(r["type"], 0) + r["devices"]

        import json
        chart_labels = json.dumps(list(type_counts.keys()))
        chart_values = json.dumps(list(type_counts.values()))

        total_devices = sum(r["devices"] for r in rows_data)

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Location Inventory Report — Link3</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
{HTML_STYLE}
</head>
<body>

<div class="header">
  <h1>📍 Location Inventory Report — Link3 Technologies Ltd.</h1>
  <p>Technology Department | Nautobot v3.0.6 | Total Locations: {len(rows_data)}</p>
</div>

<div class="filters">
  <label>Location Type:</label>
  <select id="fType"><option value="">All Types</option>{type_opts}</select>
  <label>Search:</label>
  <input type="text" id="fSearch" placeholder="Location name...">
  <label>Min Devices:</label>
  <input type="number" id="fMinDevices" placeholder="0" style="width:80px">
  <button class="btn-filter" onclick="applyFilters()">🔍 Filter</button>
  <button class="btn-reset" onclick="resetFilters()">↺ Reset</button>
  <button class="btn-csv" onclick="downloadCSV()">⬇ CSV</button>
  <button class="btn-pdf" onclick="window.print()">🖨 PDF</button>
</div>

<div class="kpi-row">
  <div class="kpi"><h2>{len(rows_data)}</h2><p>Total Locations</p></div>
  <div class="kpi"><h2>{len(loc_types)}</h2><p>Location Types</p></div>
  <div class="kpi"><h2>{total_devices}</h2><p>Total Devices</p></div>
  <div class="kpi"><h2 id="kShowing">{len(rows_data)}</h2><p>Showing</p></div>
</div>

<div class="content">
  <div class="chart-box">
    <h3>📊 Devices by Location Type</h3>
    <canvas id="typeChart" height="80"></canvas>
  </div>

  <table id="locTable">
    <thead><tr>
      <th>Location Name</th><th>Type</th><th>Parent</th>
      <th>Status</th><th>Device Count</th><th>Usage Bar</th>
    </tr></thead>
    <tbody id="tableBody"></tbody>
  </table>
</div>

<div class="footer">Link3 Technologies Ltd. — Technology Department | Confidential</div>

<script>
const ALL_DATA = {rows_js};
const MAX_DEVICES = {max_devices};

new Chart(document.getElementById('typeChart'), {{
  type: 'bar',
  data: {{
    labels: {chart_labels},
    datasets: [{{
      label: 'Total Devices',
      data: {chart_values},
      backgroundColor: '#2E75B6'
    }}]
  }},
  options: {{
    responsive: true,
    plugins: {{ legend: {{ display: false }} }},
    scales: {{ y: {{ beginAtZero: true }} }}
  }}
}});

function renderTable(data) {{
  document.getElementById('kShowing').textContent = data.length;
  document.getElementById('tableBody').innerHTML = data.map(r => {{
    const pct = MAX_DEVICES > 0 ? Math.round((r.devices / MAX_DEVICES) * 100) : 0;
    return `<tr>
      <td><strong>${{r.name}}</strong></td>
      <td>${{r.type}}</td>
      <td>${{r.parent}}</td>
      <td>${{r.status}}</td>
      <td><strong>${{r.devices}}</strong></td>
      <td>
        <div class="bar-wrap">
          <div class="bar-fill" style="width:${{pct}}%"></div>
        </div>
      </td>
    </tr>`;
  }}).join('');
}}

function applyFilters() {{
  const type = document.getElementById('fType').value;
  const search = document.getElementById('fSearch').value.toLowerCase();
  const minDev = parseInt(document.getElementById('fMinDevices').value) || 0;
  renderTable(ALL_DATA.filter(r =>
    (!type || r.type === type) &&
    (!search || r.name.toLowerCase().includes(search)) &&
    (r.devices >= minDev)
  ));
}}

function resetFilters() {{
  document.getElementById('fType').value = '';
  document.getElementById('fSearch').value = '';
  document.getElementById('fMinDevices').value = '';
  renderTable(ALL_DATA);
}}

function downloadCSV() {{
  const type = document.getElementById('fType').value;
  const search = document.getElementById('fSearch').value.toLowerCase();
  const minDev = parseInt(document.getElementById('fMinDevices').value) || 0;
  const data = ALL_DATA.filter(r =>
    (!type || r.type === type) &&
    (!search || r.name.toLowerCase().includes(search)) &&
    (r.devices >= minDev)
  );
  let csv = 'Location Name,Type,Parent,Status,Device Count\\n';
  data.forEach(r => {{
    csv += `"${{r.name}}","${{r.type}}","${{r.parent}}","${{r.status}}",${{r.devices}}\\n`;
  }});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([csv], {{type:'text/csv'}}));
  a.download = 'link3_location_report.csv';
  a.click();
}}

renderTable(ALL_DATA);
</script>
</body></html>"""

        self.create_file("location_report.html", html)
        self.logger.info(f"Location Report generated! {len(rows_data)} locations found.")


register_jobs(LocationInventoryReport)

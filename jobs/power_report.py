from nautobot.apps.jobs import Job, register_jobs
from nautobot.dcim.models import PowerFeed, PowerPanel

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
  .section-title { font-size: 16px; font-weight: bold; color: #1F4E79;
                   margin: 24px 0 12px; padding-left: 40px; }
  .content { padding: 0 40px 20px; }
  table { width: 100%; border-collapse: collapse; background: white;
          border-radius: 8px; overflow: hidden; margin-bottom: 24px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
  th { background: #1F4E79; color: white; padding: 10px 12px;
       text-align: left; font-size: 13px; }
  td { padding: 9px 12px; border-bottom: 1px solid #EBF3FB; font-size: 13px; }
  tr:hover { background: #F0F4F8; }
  .status-active { color: #375623; font-weight: bold; }
  .status-other { color: #843C0C; font-weight: bold; }
  .util-high { color: #843C0C; font-weight: bold; }
  .util-ok { color: #375623; }
  .footer { text-align: center; padding: 20px; font-size: 12px; color: #595959; }
  @media print {
    .filters { display: none !important; }
    body { background: white; }
  }
</style>
"""

class PowerReport(Job):
    class Meta:
        name = "8. Power & PDU Report"
        description = "Power feeds and panels with utilization — filterable, CSV & PDF"
        has_sensitive_variables = False

    def run(self):
        feeds = PowerFeed.objects.all().order_by("power_panel__location__name", "name")
        panels = PowerPanel.objects.all().order_by("location__name", "name")

        feeds_data = []
        statuses = set()
        locations = set()

        for feed in feeds:
            panel = feed.power_panel.name if feed.power_panel else "—"
            location = feed.power_panel.location.name if feed.power_panel and feed.power_panel.location else "—"
            status = feed.status.name if feed.status else "Unknown"
            feed_type = feed.type if feed.type else "—"
            voltage = str(feed.voltage) if feed.voltage else "—"
            amperage = str(feed.amperage) if feed.amperage else "—"
            max_utilization = str(feed.max_utilization) if feed.max_utilization else "—"

            statuses.add(status)
            locations.add(location)

            feeds_data.append({
                "name": feed.name,
                "panel": panel,
                "location": location,
                "status": status,
                "type": feed_type,
                "voltage": voltage,
                "amperage": amperage,
                "max_util": max_utilization,
            })

        panels_data = []
        for panel in panels:
            location = panel.location.name if panel.location else "—"
            feed_count = panel.powerfeeds.count()
            panels_data.append({
                "name": panel.name,
                "location": location,
                "feed_count": feed_count,
            })

        status_opts = "".join(f'<option value="{s}">{s}</option>' for s in sorted(statuses))
        location_opts = "".join(f'<option value="{l}">{l}</option>' for l in sorted(locations))

        feeds_js = str(feeds_data).replace("'", '"').replace('True','true').replace('False','false').replace('None','null')
        panels_js = str(panels_data).replace("'", '"').replace('True','true').replace('False','false').replace('None','null')

        active_feeds = sum(1 for f in feeds_data if f["status"] == "Active")

        html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Power Report — Link3</title>
{HTML_STYLE}</head>
<body>

<div class="header">
  <h1>⚡ Power & PDU Report — Link3 Technologies Ltd.</h1>
  <p>Technology Department | Nautobot v3.0.6</p>
</div>

<div class="filters">
  <label>Location:</label>
  <select id="fLocation"><option value="">All</option>{location_opts}</select>
  <label>Status:</label>
  <select id="fStatus"><option value="">All</option>{status_opts}</select>
  <label>Search:</label>
  <input type="text" id="fSearch" placeholder="Feed name...">
  <button class="btn-filter" onclick="applyFilters()">🔍 Filter</button>
  <button class="btn-reset" onclick="resetFilters()">↺ Reset</button>
  <button class="btn-csv" onclick="downloadCSV()">⬇ CSV</button>
  <button class="btn-pdf" onclick="window.print()">🖨 PDF</button>
</div>

<div class="kpi-row">
  <div class="kpi"><h2>{len(feeds_data)}</h2><p>Total Power Feeds</p></div>
  <div class="kpi"><h2>{active_feeds}</h2><p>Active Feeds</p></div>
  <div class="kpi"><h2>{len(panels_data)}</h2><p>Power Panels</p></div>
  <div class="kpi"><h2 id="kShowing">{len(feeds_data)}</h2><p>Showing</p></div>
</div>

<div class="section-title">⚡ Power Feeds</div>
<div class="content">
  <table id="feedTable">
    <thead><tr>
      <th>Feed Name</th><th>Panel</th><th>Location</th><th>Status</th>
      <th>Type</th><th>Voltage</th><th>Amperage</th><th>Max Util %</th>
    </tr></thead>
    <tbody id="feedBody"></tbody>
  </table>
</div>

<div class="section-title">🔌 Power Panels</div>
<div class="content">
  <table>
    <thead><tr>
      <th>Panel Name</th><th>Location</th><th>Feed Count</th>
    </tr></thead>
    <tbody>
      {"".join(f'<tr><td><strong>{p["name"]}</strong></td><td>{p["location"]}</td><td>{p["feed_count"]}</td></tr>' for p in panels_data)}
    </tbody>
  </table>
</div>

<div class="footer">Link3 Technologies Ltd. — Technology Department | Confidential</div>

<script>
const FEEDS = {feeds_js};

function renderFeeds(data) {{
  document.getElementById('kShowing').textContent = data.length;
  document.getElementById('feedBody').innerHTML = data.map(f => `
    <tr>
      <td><strong>${{f.name}}</strong></td>
      <td>${{f.panel}}</td>
      <td>${{f.location}}</td>
      <td class="${{f.status === 'Active' ? 'status-active' : 'status-other'}}">${{f.status}}</td>
      <td>${{f.type}}</td>
      <td>${{f.voltage}}V</td>
      <td>${{f.amperage}}A</td>
      <td class="${{parseInt(f.max_util) >= 80 ? 'util-high' : 'util-ok'}}">${{f.max_util}}%</td>
    </tr>`).join('');
}}

function applyFilters() {{
  const loc = document.getElementById('fLocation').value;
  const status = document.getElementById('fStatus').value;
  const search = document.getElementById('fSearch').value.toLowerCase();
  renderFeeds(FEEDS.filter(f =>
    (!loc || f.location === loc) &&
    (!status || f.status === status) &&
    (!search || f.name.toLowerCase().includes(search))
  ));
}}

function resetFilters() {{
  ['fLocation','fStatus'].forEach(id => document.getElementById(id).value = '');
  document.getElementById('fSearch').value = '';
  renderFeeds(FEEDS);
}}

function downloadCSV() {{
  const loc = document.getElementById('fLocation').value;
  const status = document.getElementById('fStatus').value;
  const search = document.getElementById('fSearch').value.toLowerCase();
  const data = FEEDS.filter(f =>
    (!loc || f.location === loc) &&
    (!status || f.status === status) &&
    (!search || f.name.toLowerCase().includes(search))
  );
  let csv = 'Feed Name,Panel,Location,Status,Type,Voltage,Amperage,Max Util%\\n';
  data.forEach(f => {{
    csv += `"${{f.name}}","${{f.panel}}","${{f.location}}","${{f.status}}","${{f.type}}","${{f.voltage}}","${{f.amperage}}","${{f.max_util}}"\\n`;
  }});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([csv], {{type:'text/csv'}}));
  a.download = 'link3_power_report.csv';
  a.click();
}}

renderFeeds(FEEDS);
</script>
</body></html>"""

        self.create_file("power_report.html", html)
        self.logger.info(f"Power Report generated! {len(feeds_data)} feeds, {len(panels_data)} panels.")


register_jobs(PowerReport)

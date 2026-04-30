from nautobot.apps.jobs import Job, register_jobs
from nautobot.virtualization.models import VirtualMachine

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
    border-radius: 4px; font-size: 13px; color: #1F4E79; }
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
  th { background: #1F4E79; color: white; padding: 10px 12px; text-align: left;
       font-size: 13px; }
  td { padding: 9px 12px; border-bottom: 1px solid #EBF3FB; font-size: 13px; }
  tr:hover { background: #F0F4F8; }
  .status-active { color: #375623; font-weight: bold; }
  .status-other { color: #843C0C; font-weight: bold; }
  .count-badge { background: #EBF3FB; color: #1F4E79; padding: 4px 10px;
                 border-radius: 12px; font-size: 12px; font-weight: bold;
                 display: inline-block; margin-left: 8px; }
  .footer { text-align: center; padding: 20px; font-size: 12px; color: #595959; }
  @media print {
    .filters, .btn-csv, .btn-pdf { display: none !important; }
    body { background: white; }
    .kpi-row { break-inside: avoid; }
  }
</style>
"""

class VirtualMachineReport(Job):
    class Meta:
        name = "7. Virtual Machine Report"
        description = "All VMs with cluster, role, platform, IP — filterable, CSV & PDF"
        has_sensitive_variables = False

    def run(self):
        vms = VirtualMachine.objects.all().order_by("cluster__name", "name")
        if not vms.exists():
            self.logger.warning("No virtual machines found in Nautobot!")
            return

        rows_data = []
        clusters = set()
        statuses = set()
        roles = set()

        for vm in vms:
            cluster = vm.cluster.name if vm.cluster else "—"
            status = vm.status.name if vm.status else "Unknown"
            role = vm.role.name if vm.role else "—"
            platform = vm.platform.name if vm.platform else "—"
            ip = vm.primary_ip.address if vm.primary_ip else "—"
            try:
    vcpus = str(vm.vcpus) if vm.vcpus else "—"
except Exception:
    vcpus = "—"
try:
    memory = f"{vm.memory} MB" if vm.memory else "—"
except Exception:
    memory = "—"
try:
    disk = f"{vm.disk} GB" if vm.disk else "—"
except Exception:
    disk = "—"

            clusters.add(cluster)
            statuses.add(status)
            roles.add(role)

            rows_data.append({
                "name": vm.name,
                "cluster": cluster,
                "status": status,
                "role": role,
                "platform": platform,
                "ip": ip,
                "vcpus": vcpus,
                "memory": memory,
                "disk": disk,
            })

        cluster_opts = "".join(f'<option value="{c}">{c}</option>' for c in sorted(clusters))
        status_opts = "".join(f'<option value="{s}">{s}</option>' for s in sorted(statuses))
        role_opts = "".join(f'<option value="{r}">{r}</option>' for r in sorted(roles))

        rows_js = str(rows_data).replace("'", '"').replace('True', 'true').replace('False', 'false').replace('None', 'null')

        active_count = sum(1 for r in rows_data if r["status"] == "Active")
        cluster_count = len(clusters)

        html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>VM Report — Link3</title>
{HTML_STYLE}</head>
<body>
<div class="header">
  <h1>🖥️ Virtual Machine Report — Link3 Technologies Ltd.</h1>
  <p>Technology Department | Nautobot v3.0.6 | Total VMs: {len(rows_data)}</p>
</div>

<div class="filters">
  <label>Cluster:</label>
  <select id="fCluster"><option value="">All</option>{cluster_opts}</select>
  <label>Status:</label>
  <select id="fStatus"><option value="">All</option>{status_opts}</select>
  <label>Role:</label>
  <select id="fRole"><option value="">All</option>{role_opts}</select>
  <label>Search:</label>
  <input type="text" id="fSearch" placeholder="VM name...">
  <button class="btn-filter" onclick="applyFilters()">🔍 Filter</button>
  <button class="btn-reset" onclick="resetFilters()">↺ Reset</button>
  <button class="btn-csv" onclick="downloadCSV()">⬇ CSV</button>
  <button class="btn-pdf" onclick="window.print()">🖨 PDF</button>
</div>

<div class="kpi-row">
  <div class="kpi"><h2 id="kTotal">{len(rows_data)}</h2><p>Total VMs</p></div>
  <div class="kpi"><h2 id="kActive">{active_count}</h2><p>Active VMs</p></div>
  <div class="kpi"><h2>{cluster_count}</h2><p>Clusters</p></div>
  <div class="kpi"><h2 id="kShowing">{len(rows_data)}</h2><p>Showing</p></div>
</div>

<div class="content">
  <table id="vmTable">
    <thead><tr>
      <th>VM Name</th><th>Cluster</th><th>Status</th><th>Role</th>
      <th>Platform</th><th>Primary IP</th><th>vCPUs</th><th>Memory</th><th>Disk</th>
    </tr></thead>
    <tbody id="tableBody"></tbody>
  </table>
</div>

<div class="footer">Link3 Technologies Ltd. — Technology Department | Confidential</div>

<script>
const ALL_DATA = {rows_js};

function renderTable(data) {{
  const tbody = document.getElementById('tableBody');
  document.getElementById('kShowing').textContent = data.length;
  tbody.innerHTML = data.map(r => `
    <tr>
      <td><strong>${{r.name}}</strong></td>
      <td>${{r.cluster}}</td>
      <td class="${{r.status === 'Active' ? 'status-active' : 'status-other'}}">${{r.status}}</td>
      <td>${{r.role}}</td>
      <td>${{r.platform}}</td>
      <td>${{r.ip}}</td>
      <td>${{r.vcpus}}</td>
      <td>${{r.memory}}</td>
      <td>${{r.disk}}</td>
    </tr>`).join('');
}}

function applyFilters() {{
  const cluster = document.getElementById('fCluster').value;
  const status = document.getElementById('fStatus').value;
  const role = document.getElementById('fRole').value;
  const search = document.getElementById('fSearch').value.toLowerCase();
  const filtered = ALL_DATA.filter(r =>
    (!cluster || r.cluster === cluster) &&
    (!status || r.status === status) &&
    (!role || r.role === role) &&
    (!search || r.name.toLowerCase().includes(search))
  );
  renderTable(filtered);
}}

function resetFilters() {{
  ['fCluster','fStatus','fRole'].forEach(id => document.getElementById(id).value = '');
  document.getElementById('fSearch').value = '';
  renderTable(ALL_DATA);
}}

function downloadCSV() {{
  const cluster = document.getElementById('fCluster').value;
  const status = document.getElementById('fStatus').value;
  const role = document.getElementById('fRole').value;
  const search = document.getElementById('fSearch').value.toLowerCase();
  const data = ALL_DATA.filter(r =>
    (!cluster || r.cluster === cluster) &&
    (!status || r.status === status) &&
    (!role || r.role === role) &&
    (!search || r.name.toLowerCase().includes(search))
  );
  let csv = 'VM Name,Cluster,Status,Role,Platform,Primary IP,vCPUs,Memory,Disk\\n';
  data.forEach(r => {{
    csv += `"${{r.name}}","${{r.cluster}}","${{r.status}}","${{r.role}}","${{r.platform}}","${{r.ip}}","${{r.vcpus}}","${{r.memory}}","${{r.disk}}"\\n`;
  }});
  const blob = new Blob([csv], {{type: 'text/csv'}});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'link3_vm_report.csv';
  a.click();
}}

renderTable(ALL_DATA);
</script>
</body></html>"""

        self.create_file("vm_report.html", html)
        self.logger.info(f"VM Report generated! {len(rows_data)} VMs found. Download above.")


register_jobs(VirtualMachineReport)

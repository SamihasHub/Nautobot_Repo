from nautobot.apps.jobs import Job, register_jobs
from nautobot.ipam.models import Prefix

HTML_STYLE = """
<style>
  body { font-family: Arial, sans-serif; margin: 40px; color: #1F4E79; }
  h1 { background: #1F4E79; color: white; padding: 16px; border-radius: 6px; }
  table { width: 100%; border-collapse: collapse; margin-top: 20px; }
  th { background: #1F4E79; color: white; padding: 10px; text-align: left; }
  td { padding: 9px 10px; border-bottom: 1px solid #AABBD4; }
  tr:nth-child(even) { background: #EBF3FB; }
  .high { color: #843C0C; font-weight: bold; }
  .summary { background: #E2EFDA; border-left: 5px solid #375623;
             padding: 12px 16px; margin-top: 24px; border-radius: 4px; }
  .footer { margin-top: 40px; font-size: 12px; color: #595959; text-align: center; }
</style>
"""

class IPUtilizationReport(Job):
    class Meta:
        name = "2. IP Utilization Report"
        description = "Generates a PDF-ready HTML report of prefix usage across all locations"
        has_sensitive_variables = False

    def run(self):
        prefixes = Prefix.objects.all().order_by("network")
        if not prefixes.exists():
            self.logger.warning("No prefixes found!")
            return

        rows = ""
        high_count = 0

        for prefix in prefixes:
            # v3 returns a tuple (used, total) — handle both cases
            try:
                util_raw = prefix.get_utilization()
                if isinstance(util_raw, tuple):
                    used, total = util_raw
                    pct = round((used / total * 100), 1) if total else 0.0
                else:
                    pct = round(float(util_raw) * 100, 1)
            except Exception:
                pct = 0.0

            location = prefix.location.name if prefix.location else "Global"
            status = prefix.status.name if prefix.status else "—"
            vrf_list = prefix.vrfs.all()
          vrf = vrf_list.first().name if vrf_list.exists() else "Global"
            flag = ""
            css = ""
            if pct >= 80:
                flag = "⚠️ HIGH"
                css = 'class="high"'
                high_count += 1

            rows += f"""
            <tr>
              <td {css}>{prefix.prefix}</td>
              <td>{location}</td>
              <td>{vrf}</td>
              <td {css}>{pct}%</td>
              <td>{status}</td>
              <td {css}>{flag}</td>
            </tr>"""

        html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>IP Utilization Report</title>
{HTML_STYLE}</head><body>
<h1>🌐 IP Utilization Report — Link3 Technologies Ltd.</h1>
<p>Total Prefixes: <strong>{prefixes.count()}</strong> |
   High Utilization (≥80%): <strong>{high_count}</strong></p>
<table>
  <thead><tr>
    <th>Prefix</th><th>Location</th><th>VRF</th>
    <th>Utilization</th><th>Status</th><th>Flag</th>
  </tr></thead>
  <tbody>{rows}</tbody>
</table>
<div class="summary">
  <strong>Summary:</strong> {prefixes.count()} total prefixes |
  {high_count} prefixes above 80% — action required!
</div>
<div class="footer">Link3 Technologies Ltd. — Technology Department | Nautobot v3.0.6</div>
</body></html>"""

        self.create_file("ip_utilization_report.html", html)
        self.logger.info(f"Report generated! {prefixes.count()} prefixes. Download the file above.")


register_jobs(IPUtilizationReport)

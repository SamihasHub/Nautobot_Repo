from nautobot.apps.jobs import Job, register_jobs
from nautobot.circuits.models import Circuit

HTML_STYLE = """
<style>
  body { font-family: Arial, sans-serif; margin: 40px; color: #1F4E79; }
  h1 { background: #1F4E79; color: white; padding: 16px; border-radius: 6px; }
  table { width: 100%; border-collapse: collapse; margin-top: 20px; }
  th { background: #1F4E79; color: white; padding: 10px; text-align: left; }
  td { padding: 9px 10px; border-bottom: 1px solid #AABBD4; }
  tr:nth-child(even) { background: #EBF3FB; }
  .active { color: #375623; font-weight: bold; }
  .decom { color: #843C0C; font-weight: bold; }
  .prov { color: #2E75B6; font-weight: bold; }
  .summary { background: #E2EFDA; border-left: 5px solid #375623;
             padding: 12px 16px; margin-top: 24px; border-radius: 4px; }
  .footer { margin-top: 40px; font-size: 12px; color: #595959; text-align: center; }
</style>
"""

class CircuitStatusReport(Job):
    class Meta:
        name = "3. Circuit Status Report"
        description = "Generates a PDF-ready HTML report of all circuits by status"
        has_sensitive_variables = False

    def run(self):
        circuits = Circuit.objects.all().order_by("status__name", "cid")
        if not circuits.exists():
            self.logger.warning("No circuits found!")
            return

        rows = ""
        active = decommissioned = provisioning = other = 0
        for circuit in circuits:
            status = circuit.status.name if circuit.status else "Unknown"
            provider = circuit.provider.name if circuit.provider else "—"
            ctype = circuit.circuit_type.name if circuit.circuit_type else "—"
            bandwidth = f"{circuit.commit_rate} Kbps" if circuit.commit_rate else "—"
            if status == "Active":
                active += 1
                css = 'class="active"'
            elif status == "Decommissioned":
                decommissioned += 1
                css = 'class="decom"'
            elif status == "Provisioning":
                provisioning += 1
                css = 'class="prov"'
            else:
                other += 1
                css = ""
            rows += f"""
            <tr>
              <td>{circuit.cid}</td>
              <td>{provider}</td>
              <td>{ctype}</td>
              <td {css}>{status}</td>
              <td>{bandwidth}</td>
            </tr>"""

        html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Circuit Status Report</title>
{HTML_STYLE}</head><body>
<h1>🔌 Circuit Status Report — Link3 Technologies Ltd.</h1>
<p>Total Circuits: <strong>{circuits.count()}</strong></p>
<table>
  <thead><tr>
    <th>Circuit ID</th><th>Provider</th><th>Type</th>
    <th>Status</th><th>Bandwidth</th>
  </tr></thead>
  <tbody>{rows}</tbody>
</table>
<div class="summary">
  <strong>Summary:</strong> Active: {active} | Provisioning: {provisioning} |
  Decommissioned: {decommissioned} | Other: {other}
</div>
<div class="footer">Link3 Technologies Ltd. — Technology Department | Nautobot v3.0.6</div>
</body></html>"""

        self.create_file("circuit_status_report.html", html)
        self.logger.info(f"Report generated! {circuits.count()} circuits found. Download the file above.")


register_jobs(CircuitStatusReport)

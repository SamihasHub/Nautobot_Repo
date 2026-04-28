from nautobot.apps.jobs import Job, register_jobs
from nautobot.dcim.models import Device

HTML_STYLE = """
<style>
  body { font-family: Arial, sans-serif; margin: 40px; color: #1F4E79; }
  h1 { background: #1F4E79; color: white; padding: 16px; border-radius: 6px; }
  table { width: 100%; border-collapse: collapse; margin-top: 20px; }
  th { background: #1F4E79; color: white; padding: 10px; text-align: left; }
  td { padding: 9px 10px; border-bottom: 1px solid #AABBD4; }
  tr:nth-child(even) { background: #EBF3FB; }
  .active { color: #375623; font-weight: bold; }
  .inactive { color: #843C0C; font-weight: bold; }
  .summary { background: #E2EFDA; border-left: 5px solid #375623;
             padding: 12px 16px; margin-top: 24px; border-radius: 4px; }
  .footer { margin-top: 40px; font-size: 12px; color: #595959; text-align: center; }
</style>
"""

class BTSHealthReport(Job):
    class Meta:
        name = "4. BTS Health Report"
        description = "All devices at BTS locations with status and custom field data"
        has_sensitive_variables = False

    def run(self):
        # Filter by location name containing 'BTS'
      bts_devices = Device.objects.filter(
        name__icontains="BTS"
      ).order_by("location__name", "name")
      
        if not bts_devices.exists():
            self.logger.warning(
                "No devices found at BTS locations! "
                "Listing ALL devices with their locations for reference..."
            )
            # Show all locations to help identify correct names
            all_devices = Device.objects.all()[:20]
            for d in all_devices:
                loc = d.location.name if d.location else "No Location"
                self.logger.info(f"Device: {d.name} | Location: {loc}")
            return

        rows = ""
        active = inactive = 0

        for device in bts_devices:
            location = device.location.name if device.location else "—"
            status = device.status.name if device.status else "Unknown"
            role = device.role.name if device.role else "—"
            bts_type = device.custom_field_data.get("bts_type", "—")
            support_office = device.custom_field_data.get("support_office", "—")

            if status == "Active":
                active += 1
                css = 'class="active"'
            else:
                inactive += 1
                css = 'class="inactive"'

            rows += f"""
            <tr>
              <td>{device.name}</td>
              <td>{location}</td>
              <td>{role}</td>
              <td {css}>{status}</td>
              <td>{bts_type}</td>
              <td>{support_office}</td>
            </tr>"""

        html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>BTS Health Report</title>
{HTML_STYLE}</head><body>
<h1>📡 BTS Health Report — Link3 Technologies Ltd.</h1>
<p>Total Devices at BTS Locations: <strong>{bts_devices.count()}</strong></p>
<table>
  <thead><tr>
    <th>Device Name</th><th>Location</th><th>Role</th>
    <th>Status</th><th>BTS Type</th><th>Support Office</th>
  </tr></thead>
  <tbody>{rows}</tbody>
</table>
<div class="summary">
  <strong>Summary:</strong> Active: {active} | Inactive: {inactive} |
  Total: {active + inactive}
</div>
<div class="footer">Link3 Technologies Ltd. — Technology Department | Nautobot v3.0.6</div>
</body></html>"""

        self.create_file("bts_health_report.html", html)
        self.logger.info(
            f"Report generated! {bts_devices.count()} devices at BTS locations. "
            "Download the file above."
        )


register_jobs(BTSHealthReport)

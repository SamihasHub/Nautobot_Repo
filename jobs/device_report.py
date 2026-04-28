import os
import pandas as pd
from collections import Counter

from nautobot.apps.jobs import Job, register_jobs
from nautobot.dcim.models import Device

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors


class ActiveDeviceReport(Job):

    class Meta:
        name = "1. Device Inventory Report"
        description = "Device report with Excel/PDF export"
        has_sensitive_variables = False

    def run(self):
        devices = Device.objects.filter(status__name="Active")

        if not devices.exists():
            self.logger.warning("No active devices found!")
            return

        data = []

        for device in devices:
            row = {
                "Device": device.name,
                "Location": device.location.name if device.location else "N/A",
                "Role": device.role.name if device.role else "N/A",
                "Primary IP": str(device.primary_ip.address) if device.primary_ip else "N/A"
            }
            data.append(row)
            self.logger.info(row)

        self.generate_reports(data, "device_report")

    def generate_reports(self, data, filename):
        base = "/opt/nautobot/media/reports/"
        os.makedirs(base, exist_ok=True)

        df = pd.DataFrame(data)
        df.to_excel(f"{base}{filename}.xlsx", index=False)

        pdf_data = [list(data[0].keys())] + [list(d.values()) for d in data]

        doc = SimpleDocTemplate(f"{base}{filename}.pdf")
        table = Table(pdf_data)
        table.setStyle([("GRID", (0,0), (-1,-1), 1, colors.black)])
        doc.build([table])

        self.logger.info(f"Reports saved: {base}{filename}.xlsx/.pdf")


register_jobs(ActiveDeviceReport)

import os
import pandas as pd

from nautobot.apps.jobs import Job, register_jobs
from nautobot.dcim.models import Device


class BTSHealthReport(Job):

    class Meta:
        name = "4. BTS Health Report"
        description = "BTS device monitoring"

    def run(self):
        devices = Device.objects.filter(role__name__icontains="BTS")

        data = []

        for d in devices:
            row = {
                "Device": d.name,
                "Location": d.location.name if d.location else "N/A",
                "Status": d.status.name if d.status else "Unknown",
                "BTS Type": d.custom_field_data.get("bts_type", "N/A"),
                "Support Office": d.custom_field_data.get("support_office", "N/A"),
            }

            data.append(row)

        self.export(data, "bts_health")

    def export(self, data, name):
        base = "/opt/nautobot/media/reports/"
        os.makedirs(base, exist_ok=True)

        pd.DataFrame(data).to_excel(f"{base}{name}.xlsx", index=False)


register_jobs(BTSHealthReport)

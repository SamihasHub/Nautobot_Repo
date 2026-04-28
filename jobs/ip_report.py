import os
import pandas as pd

from nautobot.apps.jobs import Job, register_jobs
from nautobot.ipam.models import Prefix


class IPUtilizationReport(Job):

    class Meta:
        name = "2. IP Utilization Report"
        description = "Prefix utilization with export"

    def run(self):
        prefixes = Prefix.objects.all()

        data = []

        for p in prefixes:
            pct = round(p.get_utilization() * 100, 2)

            row = {
                "Prefix": str(p.prefix),
                "Location": p.location.name if p.location else "Global",
                "Status": p.status.name if p.status else "Unknown",
                "Utilization %": pct
            }

            data.append(row)

            if pct >= 80:
                self.logger.warning(row)
            else:
                self.logger.info(row)

        self.export(data, "ip_utilization")

    def export(self, data, name):
        base = "/opt/nautobot/media/reports/"
        os.makedirs(base, exist_ok=True)

        df = pd.DataFrame(data)
        df.to_excel(f"{base}{name}.xlsx", index=False)


register_jobs(IPUtilizationReport)

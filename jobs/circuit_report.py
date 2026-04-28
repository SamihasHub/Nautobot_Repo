import os
import pandas as pd
from collections import Counter

from nautobot.apps.jobs import Job, register_jobs
from nautobot.circuits.models import Circuit


class CircuitStatusReport(Job):

    class Meta:
        name = "3. Circuit Status Report"
        description = "Circuit breakdown report"

    def run(self):
        circuits = Circuit.objects.all()

        data = []
        status_counter = Counter()

        for c in circuits:
            status = c.status.name if c.status else "Unknown"

            row = {
                "CID": c.cid,
                "Provider": c.provider.name if c.provider else "Unknown",
                "Type": c.circuit_type.name if c.circuit_type else "Unknown",
                "Status": status
            }

            data.append(row)
            status_counter[status] += 1

        self.export(data, "circuit_report")

        self.logger.info(f"Summary: {dict(status_counter)}")

    def export(self, data, name):
        base = "/opt/nautobot/media/reports/"
        os.makedirs(base, exist_ok=True)

        pd.DataFrame(data).to_excel(f"{base}{name}.xlsx", index=False)


register_jobs(CircuitStatusReport)

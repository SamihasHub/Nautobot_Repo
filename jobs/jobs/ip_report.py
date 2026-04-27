from nautobot.apps.jobs import Job, register_jobs
from nautobot.ipam.models import Prefix


class IPUtilizationReport(Job):

    class Meta:
        name = "2. IP Utilization Report"
        description = "Shows prefix usage across all locations"
        has_sensitive_variables = False

    def run(self):
        prefixes = Prefix.objects.all()
        if not prefixes.exists():
            self.logger.warning("No prefixes found!")
            return
        for prefix in prefixes:
            utilization = prefix.get_utilization()
            pct = round(utilization * 100, 1)
            location = prefix.location.name if prefix.location else "Global"
            status = prefix.status.name if prefix.status else "Unknown"
            if pct >= 80:
                self.logger.warning(
                    f"[HIGH] {prefix.prefix} | {location} | {pct}% used | Status: {status}"
                )
            else:
                self.logger.info(
                    f"{prefix.prefix} | {location} | {pct}% used | Status: {status}"
                )


register_jobs(IPUtilizationReport)

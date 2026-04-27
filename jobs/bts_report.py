from nautobot.apps.jobs import Job, register_jobs
from nautobot.dcim.models import Device


class BTSHealthReport(Job):

    class Meta:
        name = "4. BTS Health Report"
        description = "All BTS devices with location and custom field data"
        has_sensitive_variables = False

    def run(self):
        bts_devices = Device.objects.filter(
            role__name__icontains="BTS"
        )
        if not bts_devices.exists():
            self.logger.warning(
                "No BTS devices found! Make sure Device Role contains 'BTS'."
            )
            return
        active = 0
        inactive = 0
        for device in bts_devices:
            location = device.location.name if device.location else "No Location"
            status = device.status.name if device.status else "Unknown"
            bts_type = device.custom_field_data.get("bts_type", "N/A")
            support_office = device.custom_field_data.get("support_office", "N/A")
            if status == "Active":
                active += 1
                self.logger.info(
                    f"[{status}] {device.name} | Location: {location} | "
                    f"BTS Type: {bts_type} | Support Office: {support_office}"
                )
            else:
                inactive += 1
                self.logger.warning(
                    f"[{status}] {device.name} | Location: {location} | "
                    f"BTS Type: {bts_type} | Support Office: {support_office}"
                )
        self.logger.info(
            f"SUMMARY — Active BTS: {active} | Inactive BTS: {inactive} | "
            f"Total: {active + inactive}"
        )


register_jobs(BTSHealthReport)

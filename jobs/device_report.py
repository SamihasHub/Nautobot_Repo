from nautobot.apps.jobs import Job, register_jobs
from nautobot.dcim.models import Device


class ActiveDeviceReport(Job):

    class Meta:
        name = "1. Device Inventory Report"
        description = "Lists all active devices by location"
        has_sensitive_variables = False

    def run(self):
        devices = Device.objects.filter(status__name="Active")
        if not devices.exists():
            self.logger.warning("No active devices found!")
            return
        for device in devices:
            location = device.location.name if device.location else "No Location"
            role = device.role.name if device.role else "No Role"
            ip = device.primary_ip.address if device.primary_ip else "No IP"
            self.logger.info(
                f"[{location}] {device.name} | Role: {role} | IP: {ip}"
            )


register_jobs(ActiveDeviceReport)

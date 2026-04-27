from nautobot.extras.jobs import Job
from nautobot.dcim.models import Device


class ActiveDeviceReport(Job):

    class Meta:
        name = "Active Device Report"
        description = "Lists all active devices in Nautobot"
        has_sensitive_variables = False

    def run(self):
        devices = Device.objects.all()
        if not devices.exists():
            self.logger.warning("No devices found in Nautobot")
            return
        for device in devices:
            self.logger.info("Found device", extra={"object": device})

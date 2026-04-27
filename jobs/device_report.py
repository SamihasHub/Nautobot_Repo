from nautobot.extras.jobs import Job
from nautobot.dcim.models import Device

class ActiveDeviceReport(Job):
    class Meta:
        name = "Active Device Report"
        description = "Lists all active devices"

    def run(self):
        devices = Device.objects.filter(status__name="Active")
        for device in devices:
            self.log_success(obj=device, message=f"{device.name}")

from nautobot.apps.jobs import register_jobs
from .device_report import ActiveDeviceReport

register_jobs(ActiveDeviceReport)

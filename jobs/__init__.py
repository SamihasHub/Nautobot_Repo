from nautobot.apps.jobs import register_jobs
from .device_report import ActiveDeviceReport
from .ip_report import IPUtilizationReport
from .circuit_report import CircuitStatusReport
from .bts_report import BTSHealthReport

register_jobs(
    ActiveDeviceReport,
    IPUtilizationReport,
    CircuitStatusReport,
    BTSHealthReport,
)

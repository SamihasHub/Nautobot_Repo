from nautobot.apps.jobs import register_jobs
from .device_report import ActiveDeviceReport
from .ip_report import IPUtilizationReport
from .circuit_report import CircuitStatusReport
from .bts_report import BTSHealthReport
from .graph_report import GraphDashboardReport
from .live_dashboard import LiveDashboardGenerator
from .vm_report import VirtualMachineReport
from .power_report import PowerReport
from .location_report import LocationInventoryReport

register_jobs(
    ActiveDeviceReport,
    IPUtilizationReport,
    CircuitStatusReport,
    BTSHealthReport,
    GraphDashboardReport,
    LiveDashboardGenerator,
    VirtualMachineReport,
    PowerReport,
    LocationInventoryReport,
)

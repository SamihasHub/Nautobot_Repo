import csv
from io import StringIO
from nautobot.apps.jobs import Job, FileVar
from nautobot.dcim.models import Device
from nautobot.ipam.models import IPAddress

name = "Network Provisioning Utilities"

class AssignPrimaryIPs(Job):
    csv_file = FileVar(
        description="Upload your 'Uploaded_Olts_Interface_IP_Binding.csv' file here."
    )

    class Meta:
        name = "Assign Loopback IPs as Primary"
        description = "Automates binding of existing Loopback interface IPs to Device Primary fields via CSV data mapping."
        has_sensitive_variables = False

    def run(self, csv_file):
        file_data = csv_file.read().decode('utf-8-sig')
        reader = csv.DictReader(StringIO(file_data))
        
        self.logger.info("Initializing automated primary IP assignment mapping process...")
        success_count = 0
        error_count = 0

        for row in reader:
            device_name = row.get('interface__device__name')
            ip_host = row.get('ip_address__host')
            
            if not device_name or not ip_host:
                continue

            try:
                device = Device.objects.get(name=device_name)
            except Device.DoesNotExist:
                self.logger.error(f"❌ Device '{device_name}' not found. Skipping.")
                error_count += 1
                continue

            try:
                ip_string = f"{ip_host.strip()}/32"
                ip_obj = IPAddress.objects.get(address=ip_string)
            except IPAddress.DoesNotExist:
                self.logger.error(f"❌ IP Address '{ip_string}' not found in IPAM modules. Skipping.")
                error_count += 1
                continue

            try:
                device.primary_ip4 = ip_obj
                device.save()
                self.logger.success(f"✅ Set {ip_string} as Primary IP for device: {device_name}")
                success_count += 1
            except Exception as e:
                self.logger.error(f"⚠️ Failed database write execution for {device_name}: {str(e)}")
                error_count += 1

        self.logger.info(f"🎉 Job Finished. Success updates: {success_count} | Errors skipped: {error_count}")

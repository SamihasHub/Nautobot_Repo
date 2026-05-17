import csv
from io import StringIO
from nautobot.apps.jobs import Job, FileVar
from nautobot.dcim.models import Device, Interface
from nautobot.ipam.models import IPAddress
from nautobot.extras.models import Status

name = "Network Provisioning Utilities"

# Changed from AssignPrimaryIPs to IpReplacement
class IpReplacement(Job):
    csv_file = FileVar(
        description="Upload your 'Infra_Routers_IP_Binding_With_32.csv' or original list here."
    )

    class Meta:
        name = "Align IP Masks to /32 & Set Primary"
        description = "Finds existing IPs, aligns masks from /24 to /32 in-place, binds them to interfaces, and assigns them as Primary Management IPs."
        has_sensitive_variables = False

    def run(self, csv_file):
        file_data = csv_file.read().decode('utf-8-sig')
        reader = csv.DictReader(StringIO(file_data))
        
        self.logger.info("Initializing advanced mask alignment and primary mapping job...")

        status_active = Status.objects.get(name="Active")
        success_count = 0
        error_count = 0

        for row in reader:
            device_name = row.get('interface__device__name') or row.get('device__name') or row.get('name') or row.get('Name')
            raw_ip = row.get('ip_address__host') or row.get('ip_address__address') or row.get('address') or row.get('IP')
            interface_name = row.get('interface__name') or row.get('interface') or 'Loopback'

            if not device_name or not raw_ip:
                continue

            ip_host = str(raw_ip).split('/')[0].strip()
            target_address = f"{ip_host}/32"

            try:
                device = Device.objects.get(name=device_name)
            except Device.DoesNotExist:
                self.logger.error(f"❌ Device '{device_name}' not found in database. Skipping.")
                error_count += 1
                continue

            try:
                interface_obj = Interface.objects.get(device=device, name=interface_name)
            except Interface.DoesNotExist:
                interface_obj = Interface.objects.create(
                    device=device,
                    name=interface_name,
                    type="virtual",
                    status=status_active
                )

            ip_obj = None

            try:
                ip_obj = IPAddress.objects.get(address=target_address)
            except IPAddress.DoesNotExist:
                pass

            if not ip_obj:
                existing_ips = IPAddress.objects.filter(address__startswith=f"{ip_host}/")
                if existing_ips.exists():
                    ip_obj = existing_ips.first()
                    old_address = ip_obj.address
                    ip_obj.address = target_address
                    ip_obj.save()
                    self.logger.warning(f"⚠️ Mask Aligned for {ip_host}: Updated {old_address} to {target_address}.")

            if not ip_obj:
                ip_obj = IPAddress.objects.create(
                    address=target_address,
                    status=status_active
                )

            try:
                ip_obj.assigned_object = interface_obj
                ip_obj.save()
            except Exception as e:
                self.logger.error(f"⚠️ Interface link failure for {device_name}: {str(e)}")

            try:
                device.primary_ip4 = ip_obj
                device.save()
                self.logger.success(f"✅ Fully configured {device_name}: Mask set to /32, bound to {interface_name}, and set as Primary.")
                success_count += 1
            except Exception as e:
                self.logger.error(f"❌ Primary update error for {device_name}: {str(e)}")
                error_count += 1

        self.logger.info(f"🎉 Process Complete! Success: {success_count} | Errors: {error_count}")

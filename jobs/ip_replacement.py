import csv
from io import StringIO
from nautobot.apps.jobs import Job, FileVar
from nautobot.dcim.models import Device, Interface
from nautobot.ipam.models import IPAddress
from nautobot.extras.models import Status

name = "Network Provisioning Utilities"

class IpReplacement(Job):
    csv_file = FileVar(
        description="Upload your custom CSV file here. The script will respect the exact mask (/32 or /24) defined per row."
    )

    class Meta:
        name = "Align IP Masks Selectively & Set Primary"
        description = "Aligns masks from /24 to /32 ONLY if specified in the CSV row, maps to interface, and sets as primary."
        has_sensitive_variables = False

    def run(self, csv_file):
        file_data = csv_file.read().decode('utf-8-sig')
        reader = csv.DictReader(StringIO(file_data))
        
        self.logger.info("Initializing selective mask alignment job...")

        status_active = Status.objects.get(name="Active")
        success_count = 0
        error_count = 0

        for row in reader:
            device_name = row.get('interface__device__name') or row.get('device__name') or row.get('name') or row.get('Name')
            raw_ip = row.get('ip_address__host') or row.get('ip_address__address') or row.get('address') or row.get('IP')
            interface_name = row.get('interface__name') or row.get('interface') or 'Loopback'

            if not device_name or not raw_ip:
                continue

            raw_ip = str(raw_ip).strip()
            
            # Dynamically detect what mask is requested in this specific CSV row
            if '/' in raw_ip:
                ip_host = raw_ip.split('/')[0].strip()
                target_mask = raw_ip.split('/')[1].strip()
            else:
                ip_host = raw_ip
                target_mask = "32" # Default to 32 if no mask is written in the row

            target_address = f"{ip_host}/{target_mask}"

            # 1. Look up the device
            try:
                device = Device.objects.get(name=device_name)
            except Device.DoesNotExist:
                self.logger.error(f"❌ Device '{device_name}' not found. Skipping.")
                error_count += 1
                continue

            # 2. Look up or create the interface
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

            # Scenario A: The exact IP/mask requested already exists perfectly
            try:
                ip_obj = IPAddress.objects.get(address=target_address)
            except IPAddress.DoesNotExist:
                pass

            # Scenario B: The exact match doesn't exist, check if the host exists with a different mask
            if not ip_obj:
                existing_ips = IPAddress.objects.filter(address__startswith=f"{ip_host}/")
                if existing_ips.exists():
                    ip_obj = existing_ips.first()
                    old_address = ip_obj.address
                    
                    # Update it to the new mask ONLY if the CSV explicitly asked for a different mask length
                    if old_address != target_address:
                        ip_obj.address = target_address
                        ip_obj.save()
                        self.logger.warning(f"⚠️ Mask Changed for {ip_host}: Converted {old_address} ➔ {target_address} based on CSV instructions.")
                    else:
                        self.logger.info(f"ℹ️ IP {old_address} already matches requested mask. No change needed.")

            # Scenario C: The IP is completely new to Nautobot
            if not ip_obj:
                ip_obj = IPAddress.objects.create(
                    address=target_address,
                    status=status_active
                )
                self.logger.info(f"✨ Created new IPAM record: {target_address}")

            # 3. Bind to interface
            try:
                ip_obj.assigned_object = interface_obj
                ip_obj.save()
            except Exception as e:
                self.logger.error(f"⚠️ Interface link failure for {device_name}: {str(e)}")

            # 4. Promote to Primary Management IP
            try:
                device.primary_ip4 = ip_obj
                device.save()
                self.logger.success(f"✅ Successfully processed {device_name} with address {target_address}")
                success_count += 1
            except Exception as e:
                self.logger.error(f"❌ Primary update error for {device_name}: {str(e)}")
                error_count += 1

        self.logger.info(f"🎉 Process Complete! Successfully updated: {success_count} devices | Errors: {error_count}")

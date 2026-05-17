import csv
from io import StringIO
from nautobot.apps.jobs import Job, FileVar
from nautobot.dcim.models import Device, Interface
from nautobot.ipam.models import IPAddress
from nautobot.extras.models import Status

name = "Network Provisioning Utilities"

class IpReplacement(Job):
    csv_file = FileVar(
        description="Upload your custom CSV file here. The script will force the exact mask (/32 or /24) defined per row."
    )

    class Meta:
        name = "Align IP Masks Selectively & Set Primary"
        description = "Forces masks from /24 to /32 via direct database query updates if specified in the CSV row."
        has_sensitive_variables = False

    def run(self, csv_file):
        file_data = csv_file.read().decode('utf-8-sig')
        reader = csv.DictReader(StringIO(file_data))
        
        self.logger.info("Initializing direct database mask alignment execution...")

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
            
            # Extract host and mask explicitly
            if '/' in raw_ip:
                ip_host = raw_ip.split('/')[0].strip()
                target_mask = raw_ip.split('/')[1].strip()
            else:
                ip_host = raw_ip
                target_mask = "32"

            target_address = f"{ip_host}/{target_mask}"

            # 1. Fetch the Device
            try:
                device = Device.objects.get(name=device_name)
            except Device.DoesNotExist:
                self.logger.error(f"❌ Device '{device_name}' not found. Skipping.")
                error_count += 1
                continue

            # 2. Get or create the interface
            interface_obj, created = Interface.objects.get_or_create(
                device=device,
                name=interface_name,
                defaults={'type': 'virtual', 'status': status_active}
            )

            # 3. Handle Direct Database IP Mask Alignment
            ip_obj = None
            
            # Look for ANY existing IP address matching this host part (regardless of its current mask)
            existing_ips = IPAddress.objects.filter(address__startswith=f"{ip_host}/")
            
            if existing_ips.exists():
                ip_obj = existing_ips.first()
                old_address = ip_obj.address
                
                if old_address != target_address:
                    # FORCE a direct database SQL update call to rewrite the mask string explicitly
                    IPAddress.objects.filter(id=ip_obj.id).update(address=target_address)
                    
                    # Refresh the local object from the database to reflect the update
                    ip_obj.refresh_from_db()
                    self.logger.warning(f"⚡ Forced Database Mask Update for {ip_host}: Changed {old_address} ➔ {target_address}")
            else:
                # If it doesn't exist anywhere, create it fresh
                ip_obj = IPAddress.objects.create(
                    address=target_address,
                    status=status_active
                )
                self.logger.info(f"✨ Created new IPAM record: {target_address}")

            # 4. Attach the IP to the interface component
            try:
                ip_obj.assigned_object = interface_obj
                ip_obj.save()
            except Exception as e:
                self.logger.error(f"⚠️ Interface link failure for {device_name}: {str(e)}")

            # 5. Set as Primary Management IP
            try:
                device.primary_ip4 = ip_obj
                device.save()
                self.logger.success(f"✅ Successfully configured {device_name} with address {target_address}")
                success_count += 1
            except Exception as e:
                self.logger.error(f"❌ Primary assignment update error for {device_name}: {str(e)}")
                error_count += 1

        self.logger.info(f"🎉 Job Complete! Successfully updated: {success_count} devices | Errors: {error_count}")

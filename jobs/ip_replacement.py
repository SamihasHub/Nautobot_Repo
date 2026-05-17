import csv
from io import StringIO
from django.db import connection  # For direct PostgreSQL execution
from nautobot.apps.jobs import Job, FileVar
from nautobot.dcim.models import Device, Interface
from nautobot.ipam.models import IPAddress
from nautobot.extras.models import Status

name = "Network Provisioning Utilities"

class IpReplacement(Job):
    csv_file = FileVar(
        description="Upload your 'Infra_Routers_IP_Binding_With_32.csv' file here."
    )

    class Meta:
        name = "Align IP Masks Selectively & Set Primary"
        description = "Bypasses all validation blocks using raw SQL to force rewrite mask modifications directly in the database table."
        has_sensitive_variables = False

    def run(self, csv_file):
        # Handle potential Excel/Windows byte order marks safely
        file_data = csv_file.read().decode('utf-8-sig')
        reader = csv.DictReader(StringIO(file_data))
        
        self.logger.info("Initializing raw backend SQL mask modification execution...")

        status_active = Status.objects.get(name="Active")
        success_count = 0
        error_count = 0

        for row in reader:
            # Strictly map the exact header strings from your uploaded file
            device_name = row.get('interface__device__name')
            raw_ip = row.get('ip_address__host')
            interface_name = row.get('interface__name') or 'Loopback'

            # If the CSV layout doesn't use those exact headers, try generic fallbacks
            if not device_name:
                device_name = row.get('device__name') or row.get('name') or row.get('Name')
            if not raw_ip:
                raw_ip = row.get('ip_address__address') or row.get('address') or row.get('IP')

            if not device_name or not raw_ip:
                self.logger.warning(f"Skipping row due to missing column data: {row}")
                continue

            raw_ip = str(raw_ip).strip()
            
            # Separate the IP address from any existing mask wrapper
            if '/' in raw_ip:
                ip_host = raw_ip.split('/')[0].strip()
                target_mask = raw_ip.split('/')[1].strip()
            else:
                ip_host = raw_ip
                target_mask = "32"

            target_address = f"{ip_host}/{target_mask}"

            # 1. Verify the Device exists in the system
            try:
                device = Device.objects.get(name=device_name)
            except Device.DoesNotExist:
                self.logger.error(f"❌ Device '{device_name}' not found. Skipping.")
                error_count += 1
                continue

            # 2. Verify or create the Interface layout component
            interface_obj, created = Interface.objects.get_or_create(
                device=device,
                name=interface_name,
                defaults={'type': 'virtual', 'status': status_active}
            )

            # 3. Target the underlying table record directly via raw SQL cursor execution
            existing_ips = IPAddress.objects.filter(address__startswith=f"{ip_host}/")
            
            if existing_ips.exists():
                ip_obj = existing_ips.first()
                old_address = ip_obj.address
                
                if old_address != target_address:
                    try:
                        with connection.cursor() as cursor:
                            # Force overwrite the value directly inside PostgreSQL table storage
                            cursor.execute(
                                "UPDATE ipam_ipaddress SET address = %s WHERE id = %s",
                                [target_address, str(ip_obj.id)]
                            )
                        
                        # Refresh object engine memory context cache completely 
                        ip_obj.refresh_from_db()
                        self.logger.warning(f"⚡ Direct SQL Mask Override: Successfully altered {old_address} ➔ {ip_obj.address}")
                    except Exception as sql_err:
                        self.logger.error(f"⚠️ SQL execution failure for {ip_host}: {str(sql_err)}")
            else:
                # If it doesn't exist anywhere, drop it in clean as a fresh instance record
                ip_obj = IPAddress.objects.create(
                    address=target_address,
                    status=status_active
                )
                self.logger.info(f"✨ Created new IPAM record: {target_address}")

            # 4. Bind the updated object to the interface component 
            try:
                ip_obj.assigned_object = interface_obj
                ip_obj.save()
            except Exception as e:
                self.logger.error(f"⚠️ Interface link assignment failure for {device_name}: {str(e)}")

            # 5. Set as Primary Management IP
            try:
                device.primary_ip4 = ip_obj
                device.save()
                self.logger.success(f"✅ Successfully configured {device_name} with address {target_address}")
                success_count += 1
            except Exception as e:
                self.logger.error(f"❌ Primary assignment update error for {device_name}: {str(e)}")
                error_count += 1

        self.logger.info(f"🎉 Job Finished! Successfully updated: {success_count} entries | Errors: {error_count}")

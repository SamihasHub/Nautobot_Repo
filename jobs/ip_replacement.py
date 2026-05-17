import csv
from io import StringIO
from django.db import connection  # Critical for raw SQL database bypass
from nautobot.apps.jobs import Job, FileVar
from nautobot.dcim.models import Device, Interface
from nautobot.ipam.models import IPAddress
from nautobot.extras.models import Status

name = "Network Provisioning Utilities"

class IpReplacement(Job):
    csv_file = FileVar(
        description="Upload your custom CSV file here. The script will force-write the exact mask (/32 or /24) defined per row via raw SQL statements."
    )

    class Meta:
        name = "Align IP Masks Selectively & Set Primary"
        description = "Bypasses Nautobot constraints using raw SQL execution statements to rewrite masks from /24 to /32 instantly in the database."
        has_sensitive_variables = False

    def run(self, csv_file):
        file_data = csv_file.read().decode('utf-8-sig')
        reader = csv.DictReader(StringIO(file_data))
        
        self.logger.info("Initializing raw backend SQL mask modification execution...")

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

            # 1. Fetch the target device
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

            # 3. Use raw SQL execution to force change mask lengths in the backend table
            existing_ips = IPAddress.objects.filter(address__startswith=f"{ip_host}/")
            
            if existing_ips.exists():
                ip_obj = existing_ips.first()
                old_address = ip_obj.address
                
                if old_address != target_address:
                    try:
                        # Establish a direct cursor connection to the PostgreSQL database engine
                        with connection.cursor() as cursor:
                            # Update the absolute value inside the database column bypassing the application layer
                            cursor.execute(
                                "UPDATE ipam_ipaddress SET address = %s WHERE id = %s",
                                [target_address, str(ip_obj.id)]
                            )
                        
                        # Reload object state directly from database transaction records
                        ip_obj.refresh_from_db()
                        self.logger.warning(f"⚡ Direct SQL Mask Override: Successfully rewrote {old_address} ➔ {ip_obj.address}")
                    except Exception as sql_err:
                        self.logger.error(f"⚠️ Raw SQL execution failed for {ip_host}: {str(sql_err)}")
            else:
                # If it doesn't exist anywhere, create it fresh
                ip_obj = IPAddress.objects.create(
                    address=target_address,
                    status=status_active
                )
                self.logger.info(f"✨ Created new IPAM record: {target_address}")

            # 4. Bind the IP address to the interface component
            try:
                ip_obj.assigned_object = interface_obj
                ip_obj.save()
            except Exception as e:
                self.logger.error(f"⚠️ Interface link failure for {device_name}: {str(e)}")

            # 5. Set as Primary Management IP
            try:
                device.primary_ip4 = ip_obj
                device.save()
                self.logger.success(f"✅ Configured {device_name} with address {target_address}")
                success_count += 1
            except Exception as e:
                self.logger.error(f"❌ Primary assignment error for {device_name}: {str(e)}")
                error_count += 1

        self.logger.info(f"🎉 Job Finished! Successfully updated: {success_count} entries | Errors: {error_count}")

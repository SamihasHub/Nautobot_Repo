import csv
from io import StringIO
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
        description = "Aligns mask lengths by updating the 'mask_length' field directly based on CSV specifications."
        has_sensitive_variables = False

    def run(self, csv_file):
        file_data = csv_file.read().decode('utf-8-sig')
        reader = csv.DictReader(StringIO(file_data))
        
        self.logger.info("Initializing precise schema field mask alignment...")

        status_active = Status.objects.get(name="Active")
        success_count = 0
        error_count = 0

        for row in reader:
            # Map headers from your CSV file
            device_name = row.get('interface__device__name')
            raw_ip = row.get('ip_address__host')
            interface_name = row.get('interface__name') or 'Loopback'

            # Fallbacks for other file schemas
            if not device_name:
                device_name = row.get('device__name') or row.get('name') or row.get('Name')
            if not raw_ip:
                raw_ip = row.get('ip_address__address') or row.get('address') or row.get('IP')

            if not device_name or not raw_ip:
                continue

            raw_ip = str(raw_ip).strip()
            
            # Parse out host string and subnet mask length
            if '/' in raw_ip:
                ip_host = raw_ip.split('/')[0].strip()
                try:
                    target_mask = int(raw_ip.split('/')[1].strip())
                except ValueError:
                    target_mask = 32
            else:
                ip_host = raw_ip
                target_mask = 32

            # 1. Fetch the Device
            try:
                device = Device.objects.get(name=device_name)
            except Device.DoesNotExist:
                self.logger.error(f"❌ Device '{device_name}' not found. Skipping.")
                error_count += 1
                continue

            # 2. Get or create the Interface
            interface_obj, created = Interface.objects.get_or_create(
                device=device,
                name=interface_name,
                defaults={'type': 'virtual', 'status': status_active}
            )

            # 3. Fetch the IP address using your system's exact 'host' field
            try:
                # Query using the verified database field 'host'
                ip_obj = IPAddress.objects.get(host=ip_host)
                
                # If the mask length in the database doesn't match the CSV, update it
                if ip_obj.mask_length != target_mask:
                    old_mask = ip_obj.mask_length
                    ip_obj.mask_length = target_mask
                    ip_obj.save()
                    self.logger.warning(f"⚡ Aligned Mask for {ip_host}: Changed /{old_mask} ➔ /{target_mask}")
                else:
                    self.logger.info(f"ℹ️ {ip_host}/{target_mask} already matches database mask.")

            except IPAddress.DoesNotExist:
                # Create the IP address using correct fields if it doesn't exist
                ip_obj = IPAddress.objects.create(
                    host=ip_host,
                    mask_length=target_mask,
                    status=status_active
                )
                self.logger.info(f"✨ Created new IPAM record: {ip_host}/{target_mask}")

            # 4. Bind the IP to the interface component
            try:
                ip_obj.assigned_object = interface_obj
                ip_obj.save()
            except Exception as e:
                self.logger.error(f"⚠️ Interface link assignment failure for {device_name}: {str(e)}")

            # 5. Set as Primary Management IP
            try:
                device.primary_ip4 = ip_obj
                device.save()
                self.logger.success(f"✅ Successfully configured {device_name} with primary IP {ip_host}/{target_mask}")
                success_count += 1
            except Exception as e:
                self.logger.error(f"❌ Primary assignment update error for {device_name}: {str(e)}")
                error_count += 1

        self.logger.info(f"🎉 Job Finished! Successfully updated: {success_count} entries | Errors: {error_count}")

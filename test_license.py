from pathlib import Path
from backend.core.license import LicenseService

license_service = LicenseService(Path("data"))

print(f"License loaded: {license_service.license is not None}")
if license_service.license:
    print(f"Customer: {license_service.license.customer_name}")
    print(f"Valid until: {license_service.license.valid_until}")
    print(f"Status: {license_service.license.status}")
    print(f"Is active: {license_service.is_active()}")
    print(f"Days remaining: {license_service.days_remaining()}")

status = license_service.get_status()
print(f"\nStatus dict:")
for key, value in status.items():
    print(f"  {key}: {value}")

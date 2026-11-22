import os
import json
import platform
import psutil
import winreg
import uuid
from datetime import datetime, timezone

#how many logical cores windows can see
def get_cpu_info():
    return {
        "logical_cores": os.cpu_count()
    }

#total and available RAM
def get_memory_info():
    memory = psutil.virtual_memory()

    return {
        "total_gb": round(memory.total / (1024 ** 3), 2),
        "available_gb": round(memory.available / (1024 ** 3), 2)
    }

#total and available space on the C drive 
def get_disk_info():
    disk = psutil.disk_usage("C:\\")

    return {
        "total_gb": round(disk.total / (1024 ** 3), 2),
        "free_gb": round(disk.free / (1024 ** 3), 2)
    }

#records MAC addresses of the VM's network adapters 
def get_network_info():
    adapters = {}

    for name, addresses in psutil.net_if_addrs().items():
        mac_addresses = []

        for address in addresses:
            if address.family == psutil.AF_LINK:
                mac_addresses.append(address.address)

        if mac_addresses:
            adapters[name] = mac_addresses

    return adapters

#These checks are read-only. They look for known virtualization-related files and registry keys without modifying anything. 
def check_vm_files():
    paths = [
        r"C:\Windows\System32\drivers\VBoxMouse.sys",
        r"C:\Windows\System32\drivers\VBoxGuest.sys",
        r"C:\Windows\System32\drivers\VBoxSF.sys",
        r"C:\Windows\System32\drivers\vmhgfs.sys",
        r"C:\Windows\System32\drivers\vmmouse.sys",
        r"C:\Program Files\VMware\VMware Tools"
    ]

    results = {}

    for path in paths:
        results[path] = os.path.exists(path)

    return results


def check_vm_registry():
    registry_paths = [
        r"HARDWARE\ACPI\DSDT\VBOX__",
        r"HARDWARE\ACPI\FADT\VBOX__",
        r"SOFTWARE\Oracle\VirtualBox Guest Additions",
        r"SOFTWARE\VMware, Inc.\VMware Tools"
    ]

    results = {}

    for path in registry_paths:
        try:
            winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path)
            results[path] = True

        except FileNotFoundError:
            results[path] = False

        except OSError:
            results[path] = False

    return results


def get_uptime():
    boot_time = psutil.boot_time()
    uptime_seconds = int(datetime.now().timestamp() - boot_time)

    return {
        "seconds": uptime_seconds,
        "hours": round(uptime_seconds / 3600, 2)
    }


def get_recent_files_count():
    recent_folder = os.path.join(
        os.environ["APPDATA"],
        r"Microsoft\Windows\Recent"
    )

    if not os.path.exists(recent_folder):
        return 0

    return len(os.listdir(recent_folder))

def collect_environment():

    environment = {
        "collection_time": datetime.now(timezone.utc).isoformat(),
        "operating_system": platform.platform(),
        "computer_name": platform.node(),

        "cpu": get_cpu_info(),
        "memory": get_memory_info(),
        "disk": get_disk_info(),

        "network_adapters": get_network_info(),

        "virtualization_files": check_vm_files(),
        "virtualization_registry": check_vm_registry(),

        "uptime": get_uptime(),
        "recent_files_count": get_recent_files_count()
    }

    return environment


def main():

    results = collect_environment()

    output_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "environment.json"
    )

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(results, file, indent=4)

    print("Environment collection completed!")
    print(f"Results saved to: {output_path}")


if __name__ == "__main__":
    main()



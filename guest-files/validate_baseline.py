
import json
import os
import platform
import sys
from pathlib import Path
from importlib.util import find_spec

# SandScope directory structure
BASE_DIR = Path(r"C:\SandScope")
ENV_DIR = BASE_DIR / "environment"
TOOLS_DIR = BASE_DIR / "tools"

ENVIRONMENT_FILE = ENV_DIR / "environment.json"
FINDINGS_FILE = ENV_DIR / "environment_findings.json"

TOOL_FOLDERS = {
    "Procmon": TOOLS_DIR / "procmon",
    "capa": TOOLS_DIR / "capa",
    "Sysmon": TOOLS_DIR / "sysmon",
}

REQUIRED_MODULES = [
    "psutil",
    "pefile",
    "yara",
    "jinja2",
]

results = []


def report(name, status, details):
    results.append(status)
    print(f"[{status}] {name}: {details}")


def find_executable(folder, possible_names):
    if not folder.exists():
        return None

    for name in possible_names:
        matches = list(folder.rglob(name))
        if matches:
            return matches[0]

    return None


print("=" * 60)
print("SandScope - Baseline Validation")
print("=" * 60)

# 1. Check operating system
if platform.system() == "Windows":
    report("Operating system", "PASS", platform.platform())
else:
    report("Operating system", "FAIL", "This project requires Windows.")

# 2. Check Python version
if sys.version_info >= (3, 13):
    report("Python version", "PASS", sys.version.split()[0])
else:
    report("Python version", "FAIL", "Python 3.13 or newer is required.")

# 3. Check required Python modules
for module in REQUIRED_MODULES:
    if find_spec(module) is not None:
        report(f"Python module: {module}", "PASS", "Available")
    else:
        report(f"Python module: {module}", "FAIL", "Not installed")

# 4. Check environment.json
if ENVIRONMENT_FILE.exists():
    try:
        with ENVIRONMENT_FILE.open("r", encoding="utf-8") as file:
            environment = json.load(file)

        required_fields = [
            "collection_time",
            "operating_system",
            "computer_name",
            "cpu",
            "memory",
            "disk",
            "network_adapters",
            "virtualization_files",
            "virtualization_registry",
            "uptime",
        ]

        missing_fields = [
            field for field in required_fields
            if field not in environment
        ]

        if not missing_fields:
            report(
                "Environment data",
                "PASS",
                "environment.json exists and contains required fields."
            )
        else:
            report(
                "Environment data",
                "FAIL",
                f"Missing fields: {missing_fields}"
            )

    except (json.JSONDecodeError, OSError) as error:
        report("Environment data", "FAIL", str(error))
else:
    report("Environment data", "FAIL", "environment.json not found.")

# 5. Check environment findings
if FINDINGS_FILE.exists():
    try:
        with FINDINGS_FILE.open("r", encoding="utf-8") as file:
            json.load(file)

        report(
            "Environment findings",
            "PASS",
            "environment_findings.json is valid JSON."
        )
    except (json.JSONDecodeError, OSError) as error:
        report("Environment findings", "FAIL", str(error))
else:
    report(
        "Environment findings",
        "FAIL",
        "environment_findings.json not found."
    )

# 6. Check Procmon
procmon = find_executable(
    TOOL_FOLDERS["Procmon"],
    ["Procmon64.exe", "Procmon.exe"]
)

if procmon:
    report("Procmon", "PASS", str(procmon))
else:
    report("Procmon", "FAIL", "Procmon executable not found.")

# 7. Check capa
capa = find_executable(
    TOOL_FOLDERS["capa"],
    ["capa.exe"]
)

if capa:
    report("capa", "PASS", str(capa))
else:
    report("capa", "FAIL", "capa.exe not found.")

# 8. Sysmon is coordinated with Person 2
sysmon = find_executable(
    TOOL_FOLDERS["Sysmon"],
    ["Sysmon64.exe", "Sysmon.exe"]
)

if sysmon:
    report(
        "Sysmon",
        "PENDING",
        "Executable found. Installation and configuration must be coordinated with Person 2."
    )
else:
    report(
        "Sysmon",
        "PENDING",
        "Not yet verified. Coordinate installation and configuration with Person 2."
    )

# 9. VMware snapshot and network checks
report(
    "VMware snapshot",
    "MANUAL",
    "Confirm the VM was restored to the approved clean-baseline snapshot."
)

report(
    "VMware network isolation",
    "MANUAL",
    "Confirm VMware Network Adapter is connected to the sandbox lan segment, not NAT or Bridged."
)


# 10. Final result
print("\n" + "=" * 60)
print("VALIDATION SUMMARY")
print("=" * 60)

passed = results.count("PASS")
failed = results.count("FAIL")
pending = results.count("PENDING")
manual = results.count("MANUAL")

print(f"Passed:  {passed}")
print(f"Failed:  {failed}")
print(f"Pending: {pending}")
print(f"Manual:  {manual}")

if failed:
    print("\nRESULT: FAIL - Fix the failed checks before proceeding.")
    exit_code = 1

elif pending or manual:
    print("\nRESULT: NOT FULLY VERIFIED - Complete pending and manual checks.")
    exit_code = 2

else:
    print("\nRESULT: PASS")
    exit_code = 0

print("\nNo sample has been executed by this validation script.")
print("=" * 60)

sys.exit(exit_code)

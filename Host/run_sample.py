import os
import shutil
import subprocess
import sys
from pathlib import Path
from getpass import getpass
import hashlib
import json

# ==========================================
# SandScope - Host Controller
# Person 1: Infrastructure & Environment
# ==========================================

# ==========================================
# VMware configuration
# ==========================================

# Automatically locate VMware on each teammate's computer.
VMRUN_PATH = shutil.which("vmrun")

if VMRUN_PATH is None:
    possible_paths = [
        Path(r"C:\Program Files (x86)\VMware\VMware Workstation\vmrun.exe"),
        Path(r"C:\Program Files\VMware\VMware Workstation\vmrun.exe")
    ]

    for path in possible_paths:
        if path.is_file():
            VMRUN_PATH = str(path)
            break

if VMRUN_PATH is None:
    raise FileNotFoundError(
        "Cannot find vmrun.exe. Check VMware Workstation installation."
    )

VMRUN = Path(VMRUN_PATH)

# Each teammate specifies their own VMX location.
VMX_VALUE = os.environ.get("SANDSCOPE_VMX")

if not VMX_VALUE:
    raise RuntimeError(
        "SANDSCOPE_VMX is not configured. "
        "Set it to the full path of your Sandbox.vmx file."
    )

VMX = Path(VMX_VALUE)

SNAPSHOT = "clean-baseline"
GUEST_USER = "analyst"

GUEST_DIR = r"C:\SandScope"
GUEST_VALIDATION_RUNNER = r"C:\SandScope\run_validate.bat"

GUEST_REPORT = r"C:\SandScope\baseline_validation.txt"
GUEST_EXIT = r"C:\SandScope\baseline_validation.exit"

PROJECT_DIR = Path(r"C:\SandScope-Host")
SAMPLES_DIR = PROJECT_DIR / "approved_samples"
LOGS_DIR = PROJECT_DIR / "logs"



def run_vmrun(*args, guest=False, password=None, timeout=120,
              allow_guest_exit_codes=()):
    """Execute a VMware command, optionally accepting guest exit codes."""

    command = [str(VMRUN), "-T", "ws"]

    if guest:
        if not password:
            raise RuntimeError("Guest password is required.")

        command += ["-gu", GUEST_USER, "-gp", password]

    command += list(args)

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout
    )

    output = (result.stdout + result.stderr).strip()

    if result.returncode != 0:
        if result.returncode not in allow_guest_exit_codes:
            raise RuntimeError(
                output or f"VMware command failed: {result.returncode}"
            )

    return output



def verify_host():
    """Check host-side paths and prepare project folders."""

    if not VMRUN.is_file():
        raise FileNotFoundError(f"vmrun not found: {VMRUN}")

    if not VMX.is_file():
        raise FileNotFoundError(f"VM configuration not found: {VMX}")

    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    print("[PASS] VMware executable found.")
    print("[PASS] VM configuration found.")
    print("[PASS] Host project folders ready.")


def verify_vm():
    """Confirm that the configured VM is running."""

    output = run_vmrun("list")

    if str(VMX).lower() not in output.lower():
        raise RuntimeError("Sandbox VM is not running.")

    print("[PASS] Sandbox VM is running.")


def verify_snapshot():
    """Confirm that the expected snapshot exists."""

    output = run_vmrun("listSnapshots", str(VMX))

    if SNAPSHOT.lower() not in output.lower():
        raise RuntimeError(f"Snapshot not found: {SNAPSHOT}")

    print(f"[PASS] Snapshot exists: {SNAPSHOT}")
    print("[MANUAL] Snapshot restoration still needs confirmation.")


def verify_guest(password):
    """Test authenticated communication with the Windows guest."""

    print("\nChecking guest authentication and access...")

    output = run_vmrun(
        "directoryExistsInGuest",
        str(VMX),
        GUEST_DIR,
        guest=True,
        password=password
    )

    normalized = output.lower()

    if "not exist" in normalized or "does not exist" in normalized:
        raise RuntimeError("C:\\SandScope was not found inside the guest.")

    if "exist" not in normalized:
        raise RuntimeError(
            "Could not confirm the guest directory. "
            f"VMware response: {output}"
        )

    print("[PASS] Host authenticated with the Windows guest.")
    print("[PASS] C:\\SandScope is accessible.")


def run_guest_validation(password):
    """Run validation inside the guest and retrieve its real results."""

    print("\nRunning guest-side baseline validation...")

    # Remove previous results so an old report cannot be mistaken
    # for the result of this validation run.
    # Run the guest-side batch file directly.
	
    # Run the guest-side batch file.
    run_vmrun(
        "runProgramInGuest",
        str(VMX),
        r"C:\Windows\System32\cmd.exe",
        "/c",
        GUEST_VALIDATION_RUNNER,
        guest=True,
        password=password,
        timeout=180,
	allow_guest_exit_codes=(1, 2)
    )

    # Retrieve the report and exit-code files.
    host_report = LOGS_DIR / "baseline_validation.txt"
    host_exit = LOGS_DIR / "baseline_validation.exit"

    run_vmrun(
        "copyFileFromGuestToHost",
        str(VMX),
        GUEST_REPORT,
        str(host_report),
        guest=True,
        password=password
    )

    run_vmrun(
        "copyFileFromGuestToHost",
        str(VMX),
        GUEST_EXIT,
        str(host_exit),
        guest=True,
        password=password
    )

    if not host_report.is_file() or not host_exit.is_file():
        raise RuntimeError("Guest validation result files were not retrieved.")

    report_text = host_report.read_text(encoding="utf-8")
    exit_text = host_exit.read_text(encoding="utf-8").strip()

    try:
        exit_code = int(exit_text)
    except ValueError:
        raise RuntimeError(f"Invalid guest validation exit code: {exit_text}")

    if "RESULT:" not in report_text:
        raise RuntimeError("The retrieved report does not contain a validation result.")

    print("\n========== GUEST VALIDATION REPORT ==========")
    print(report_text)
    print("=============================================")

    print(f"\n[INFO] Guest validator exit code: {exit_code}")
    print(f"[INFO] Report saved to: {host_report}")
    print(f"[INFO] Exit code saved to: {host_exit}")

    if exit_code == 0:
        print("[PASS] Guest baseline validator reports PASS.")
    elif exit_code == 1:
        print("[FAIL] Guest baseline validator found failed checks.")
    elif exit_code == 2:
        print("[PENDING] Guest baseline is not fully verified.")
    else:
        raise RuntimeError(f"Unexpected validator exit code: {exit_code}")

    return exit_code


def main():
    print("=" * 55)
    print("SandScope - Host and Guest Baseline Verification")
    print("=" * 55)

    try:
        verify_host()
        verify_vm()
        verify_snapshot()

        print("\nEnter the Windows VM account password.")
        print("Account:", GUEST_USER)

        password = getpass("VM password: ")

        if not password:
            raise RuntimeError("No password entered.")

        verify_guest(password)

        validation_result = run_guest_validation(password)

        print("\nApproval verification (no execution):")
        sample_path = SAMPLES_DIR / "harmless_simulator.py"

        verify_approved_sample(sample_path)

        print("[PASS] Approval gate verified.")
        print("[INFO] No sample transferred or executed.")

        print("\n========== CONTROLLER SUMMARY ==========")

        if validation_result == 0:
            print("[PASS] Automated guest validation completed.")
        elif validation_result == 1:
            print("[FAIL] Baseline validation failed.")
        else:
            print("[PENDING] Baseline requires further verification.")

        print("[MANUAL] Confirm VMware snapshot restoration.")
        print("[MANUAL] Confirm network adapter is on sandbox lan.")
        print("[PENDING] Coordinate Sysmon with Person 2.")

        print("\nNo sample was transferred or executed.")
        print("Sample execution remains disabled.")

    except Exception as error:
        print("\n[FAIL]", error)
        sys.exit(1)


def verify_approved_sample(sample_path):
    """
    Accept only a regular file directly inside approved_samples,
    with a matching SHA-256 entry in approval_manifest.json.
    """

    approved_dir = SAMPLES_DIR.resolve()
    manifest_path = approved_dir / "approval_manifest.json"

    candidate = Path(sample_path).resolve()

    # Reject paths outside the approved directory.
    if candidate.parent != approved_dir:
        raise RuntimeError(
            "Rejected: sample must be directly inside approved_samples."
        )

    # Reject missing files and directories.
    if not candidate.is_file():
        raise RuntimeError("Rejected: sample file does not exist.")

    # Require an explicit approval manifest.
    if not manifest_path.is_file():
        raise RuntimeError("Rejected: approval manifest is missing.")

    try:
        manifest = json.loads(
            manifest_path.read_text(encoding="utf-8")
        )
    except (json.JSONDecodeError, OSError) as error:
        raise RuntimeError(f"Invalid approval manifest: {error}")

    expected_hash = manifest.get(candidate.name)

    if not isinstance(expected_hash, str):
        raise RuntimeError("Rejected: sample is not listed as approved.")

    # Calculate the actual file hash.
    sha256 = hashlib.sha256()

    with candidate.open("rb") as sample:
        for chunk in iter(lambda: sample.read(1024 * 1024), b""):
            sha256.update(chunk)

    actual_hash = sha256.hexdigest()

    if actual_hash.lower() != expected_hash.lower():
        raise RuntimeError("Rejected: SHA-256 hash does not match.")

    print(f"[PASS] Approved sample: {candidate.name}")
    print(f"[PASS] SHA-256: {actual_hash}")

    return candidate


if __name__ == "__main__":
    main()

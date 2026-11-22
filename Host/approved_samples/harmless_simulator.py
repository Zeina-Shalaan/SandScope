from pathlib import Path
import sys
from datetime import datetime, timezone

def main():
    if len(sys.argv) != 2:
        print("Usage: harmless_simulator.py <output_directory>")
        return 1

    output_dir = Path(sys.argv[1])
    output_dir.mkdir(parents=True, exist_ok=True)

    result_file = output_dir / "simulation_result.txt"

    result_file.write_text(
        "SandScope harmless simulator completed successfully.\n"
        f"Timestamp: {datetime.now(timezone.utc).isoformat()}\n",
        encoding="utf-8"
    )

    print("[SIMULATION] Harmless test completed.")
    print(f"[SIMULATION] Result: {result_file}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
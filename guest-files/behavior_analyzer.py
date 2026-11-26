"""SandScope behavior analyzer (Person 2).

Reads the filtered events.json written by parse_logs.py (only the sample and
its child processes) and writes behavior_findings.json in the shared
indicator format.

Usage:  python behavior_analyzer.py C:\\SandScope\\out C:\\path\\to\\sample.exe
"""
import json
import sys
from pathlib import Path

VM_WORDS = ["vbox", "virtualbox", "vmmouse", "vmhgfs", "vmware", "vmtools"]
RECENT_WORDS = ["\\windows\\recent", "recentdocs"]
ACCESS_TYPES = {"file_query", "file_create", "registry_query", "registry_change"}

LONG_SLEEP_SECONDS = 45   # from the guide: alive 45 s or more...
STARTUP_SECONDS = 5       # ...ignoring the first 5 s of startup...
QUIET_MAX_EVENTS = 20     # ...with "almost no" events after that (our own choice; tune with the simulators)


def seconds(time_text):
    """'04:35:34.847092' -> seconds since midnight."""
    h, m, s = time_text.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def evidence_line(e):
    """The event as one readable log line, e.g. 'RegOpenKey HKLM\\SOFTWARE\\VMware, Inc. by sample.exe (NAME NOT FOUND)'."""
    action = e.get("operation") or e["type"]
    line = f"{e['time']} {action} {e.get('path', '')} by {Path(e['process']).name} (PID {e['pid']})"
    return line + (f" ({e['result']})" if e.get("result") else "")


def finding(indicator_id, technique, description, matches, confidence):
    first = evidence_line(matches[0])
    more = f" [+{len(matches) - 1} more matching events]" if len(matches) > 1 else ""
    return {
        "id": indicator_id,
        "source": "behavior",
        "technique": technique,
        "description": description,
        "evidence": first + more,
        "confidence": confidence,
    }


def path_matches(events, words):
    return [e for e in events
            if e["type"] in ACCESS_TYPES and any(w in e.get("path", "").lower() for w in words)]


def long_sleep(events, sample_name, capture_end):
    """The sample's own process lived >= 45 s but was nearly silent after its first 5 s."""
    own = [e for e in events if Path(e["process"]).name.lower() == sample_name]
    if not own:
        return None
    start = seconds(own[0]["time"])
    ends = [seconds(e["time"]) for e in own if e["type"] == "process_end"]
    end = ends[0] if ends else capture_end  # no exit event: it was still running when capture stopped
    alive = end - start
    later = [e for e in events if start + STARTUP_SECONDS < seconds(e["time"]) <= end]
    if alive < LONG_SLEEP_SECONDS or len(later) > QUIET_MAX_EVENTS:
        return None
    return {
        "id": "LONG_SLEEP",
        "source": "behavior",
        "technique": "T1497.003",
        "description": "The program stayed alive a long time while doing almost nothing, as if waiting out the sandbox.",
        "evidence": (f"{sample_name} alive {alive:.0f} s (from {own[0]['time']}), "
                     f"only {len(later)} events after the first {STARTUP_SECONDS} s"),
        "confidence": "low",
    }


def analyze(events, sample_name, capture_end):
    findings = []
    vm = path_matches(events, VM_WORDS)
    if vm:
        findings.append(finding("VM_REGISTRY_CHECK", "T1497.001",
                                "The program looked for VM files or registry keys.", vm, "medium"))
    sleep = long_sleep(events, sample_name, capture_end)
    if sleep:
        findings.append(sleep)
    recent = path_matches(events, RECENT_WORDS)
    if recent:
        findings.append(finding("USER_ACTIVITY_CHECK", "T1497.002",
                                "The program looked at the Recent files list, as if checking for a real user.",
                                recent, "low"))
    return findings


def main():
    if len(sys.argv) != 3:
        print("Usage: python behavior_analyzer.py <output folder> <sample path>")
        return 1
    out = Path(sys.argv[1])
    events = json.loads((out / "events.json").read_text(encoding="utf-8"))
    # Capture end = last event of the whole run (all processes), for samples still running at the end.
    all_path = out / "events_all.json"
    every = json.loads(all_path.read_text(encoding="utf-8")) if all_path.exists() else events
    capture_end = seconds(every[-1]["time"]) if every else 0

    findings = analyze(events, Path(sys.argv[2]).name.lower(), capture_end)
    (out / "behavior_findings.json").write_text(json.dumps(findings, indent=2), encoding="utf-8")
    for f in findings:
        print(f"[{f['confidence'].upper()}] {f['id']}: {f['evidence']}")
    print(f"Wrote {len(findings)} findings to {out / 'behavior_findings.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

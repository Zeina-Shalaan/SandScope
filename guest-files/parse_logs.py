"""SandScope log collector (Person 2).

Reads one run's Procmon trace (trace.csv) and Sysmon export (sysmon.xml)
and writes them as one combined, time-sorted events.json that holds only the
events of the sample and the processes it started (all events go to events_all.json).

Usage:  python parse_logs.py C:\\SandScope\\out C:\\path\\to\\sample.exe
"""
import csv
import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

NS = "{http://schemas.microsoft.com/win/2004/08/events/event}"

# Procmon operation -> our short event type. Everything else (thread events,
# ReadFile, profiling...) is dropped to keep events.json small.
PROCMON_TYPES = {
    "Process Create": "process_create",
    "Process Exit": "process_end",
    "CreateFile": "file_query",
    "QueryOpen": "file_query",
    "QueryDirectory": "file_query",
    "RegOpenKey": "registry_query",
    "RegQueryKey": "registry_query",
    "RegQueryValue": "registry_query",
    "RegEnumKey": "registry_query",
    "RegEnumValue": "registry_query",
    "RegCreateKey": "registry_change",
    "RegSetValue": "registry_change",
    "RegDeleteKey": "registry_change",
    "RegDeleteValue": "registry_change",
    "TCP Connect": "network_connect",
    "UDP Send": "network_connect",
}

SYSMON_TYPES = {
    "1": "process_create",
    "3": "network_connect",
    "5": "process_end",
    "11": "file_create",
    "12": "registry_change",
    "13": "registry_change",
    "22": "dns_query",
}


def procmon_time(text):
    """'4:35:34.8470924 AM' (local time) -> '04:35:34.847092'."""
    clock, ampm = text.split()
    hms, frac = clock.split(".")
    t = datetime.strptime(f"{hms} {ampm}", "%I:%M:%S %p")
    return f"{t:%H:%M:%S}.{frac[:6].ljust(6, '0')}"


def sysmon_time(text):
    """'2026-11-26T12:35:32.8521087Z' (UTC) -> VM local time, same format as Procmon."""
    date_part, frac = text.rstrip("Z").split(".")
    t = datetime.fromisoformat(date_part + "+00:00").astimezone()
    return f"{t:%H:%M:%S}.{frac[:6].ljust(6, '0')}"


def int_or_none(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_procmon(csv_path):
    events = []
    with open(csv_path, encoding="utf-8-sig", errors="replace", newline="") as f:
        for row in csv.DictReader(f):
            etype = PROCMON_TYPES.get(row.get("Operation", ""))
            if not etype:
                continue
            event = {
                "time": procmon_time(row["Time of Day"]),
                "source": "procmon",
                "type": etype,
                "pid": int_or_none(row.get("PID")),
                "process": row.get("Process Name", ""),
                "operation": row["Operation"],
                "path": row.get("Path", ""),
                "result": row.get("Result", ""),
                "detail": row.get("Detail", ""),
            }
            if etype == "process_create":
                # Procmon logs this on the PARENT; the new child PID is in Detail ("PID: 1234, Command line: ...").
                event["child_pid"] = int_or_none(event["detail"].split(",")[0].replace("PID:", "").strip())
            events.append(event)
    return events


def read_text_any_encoding(path):
    raw = Path(path).read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16")
    if b"\x00" in raw[:200]:  # UTF-16 without a byte-order mark
        return raw.decode("utf-16-le")
    return raw.decode("utf-8", errors="replace")


def parse_sysmon(xml_path):
    text = read_text_any_encoding(xml_path).strip()
    if not text.startswith("<Events>"):  # export made without /e:Events
        text = f"<Events>{text}</Events>"
    events = []
    for ev in ET.fromstring(text).iter(f"{NS}Event"):
        event_id = ev.findtext(f"{NS}System/{NS}EventID")
        etype = SYSMON_TYPES.get(event_id)
        if not etype:
            continue
        data = {d.get("Name"): (d.text or "") for d in ev.iter(f"{NS}Data")}
        event = {
            "time": sysmon_time(ev.find(f"{NS}System/{NS}TimeCreated").get("SystemTime")),
            "source": "sysmon",
            "type": etype,
            "event_id": int(event_id),
            "pid": int_or_none(data.get("ProcessId")),
            "process": data.get("Image", ""),
        }
        if etype == "process_create":
            event["ppid"] = int_or_none(data.get("ParentProcessId"))
            event["parent_process"] = data.get("ParentImage", "")
            event["detail"] = data.get("CommandLine", "")
        elif etype == "network_connect":
            event["path"] = f"{data.get('DestinationIp', '')}:{data.get('DestinationPort', '')}"
        elif etype == "file_create":
            event["path"] = data.get("TargetFilename", "")
        elif etype == "registry_change":
            event["path"] = data.get("TargetObject", "")
            event["detail"] = data.get("Details", "")
        elif etype == "dns_query":
            event["path"] = data.get("QueryName", "")
        events.append(event)
    return events


def sample_pids(events, sample_path):
    """PIDs of the sample and every process it started, directly or through children."""
    name = Path(sample_path).name.lower()
    pids = set()
    for e in events:
        if e["type"] != "process_create":
            continue
        if e["source"] == "sysmon" and Path(e["process"]).name.lower() == name:
            pids.add(e["pid"])
        elif e["source"] == "procmon" and Path(e.get("path", "")).name.lower() == name:
            pids.add(e.get("child_pid"))
    # Follow children until no new PID is found (grandchildren, great-grandchildren...).
    while True:
        new = set()
        for e in events:
            if e["type"] != "process_create":
                continue
            if e["source"] == "sysmon" and e.get("ppid") in pids:
                new.add(e["pid"])
            elif e["source"] == "procmon" and e["pid"] in pids:
                new.add(e.get("child_pid"))
        new -= pids | {None}
        if not new:
            break
        pids |= new
    pids.discard(None)
    # shortcut: Windows reuses PIDs, so an unrelated process that later gets a reused PID would slip in; fine for short runs, track ProcessGuid if runs get long.
    return pids


def main():
    if len(sys.argv) != 3:
        print("Usage: python parse_logs.py <output folder> <sample path>")
        return 1
    out = Path(sys.argv[1])
    events = []
    for name, parser in (("trace.csv", parse_procmon), ("sysmon.xml", parse_sysmon)):
        path = out / name
        if path.exists():
            found = parser(path)
            print(f"{name}: {len(found)} events")
            events += found
        else:
            print(f"WARNING: {path} not found, skipping.")
    # shortcut: sorts by time of day only, so a run that crosses midnight sorts wrongly; add the date if runs get that long.
    events.sort(key=lambda e: e["time"])
    # Unfiltered copy, kept for debugging and for the report's "before filtering" numbers.
    (out / "events_all.json").write_text(json.dumps(events, indent=2), encoding="utf-8")

    pids = sample_pids(events, sys.argv[2])
    if not pids:
        print(f"WARNING: no process start found for {Path(sys.argv[2]).name}; events.json will be empty.")
    kept = [e for e in events if e["pid"] in pids]
    (out / "events.json").write_text(json.dumps(kept, indent=2), encoding="utf-8")
    print(f"Sample PIDs: {sorted(pids)}")
    print(f"Kept {len(kept)} of {len(events)} events in {out / 'events.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

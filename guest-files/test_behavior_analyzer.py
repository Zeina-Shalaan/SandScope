"""Self-check for behavior_analyzer.py. Run: python test_behavior_analyzer.py"""
from behavior_analyzer import analyze


def ev(time, etype, path="", process="sample.exe", op=""):
    return {"time": time, "type": etype, "path": path, "process": process, "pid": 7000, "operation": op}


# Evasive sample: VM key, Recent folder, then 60 s of silence before exiting.
evasive = [
    ev("10:00:00.000000", "process_create", process=r"C:\s\sample.exe"),
    ev("10:00:01.000000", "registry_query", r"HKLM\SOFTWARE\VMware, Inc.\VMware Tools", op="RegOpenKey"),
    ev("10:00:02.000000", "file_query", r"C:\Users\analyst\AppData\Roaming\Microsoft\Windows\Recent", op="QueryDirectory"),
    ev("10:01:00.000000", "process_end"),
]
ids = {f["id"]: f["confidence"] for f in analyze(evasive, "sample.exe", 0)}
assert ids == {"VM_REGISTRY_CHECK": "medium", "USER_ACTIVITY_CHECK": "low", "LONG_SLEEP": "low"}, ids

# Notepad-like run: normal registry reads, exits after 3 s -> nothing.
clean = [
    ev("10:00:00.000000", "process_create", process=r"C:\Windows\System32\notepad.exe"),
    ev("10:00:01.000000", "registry_query", r"HKLM\SOFTWARE\Microsoft\Input", process="notepad.exe"),
    ev("10:00:03.000000", "process_end", process="notepad.exe"),
]
assert analyze(clean, "notepad.exe", 0) == []

# Busy long-running program: alive 60 s but many events -> not LONG_SLEEP.
busy = [ev("10:00:00.000000", "process_create")] + \
       [ev(f"10:00:{s:02d}.000000", "file_query", r"C:\data") for s in range(6, 50)] + \
       [ev("10:01:00.000000", "process_end")]
assert analyze(busy, "sample.exe", 0) == []

# Still running when capture stopped (no process_end) and quiet -> LONG_SLEEP via capture end.
running = [ev("10:00:00.000000", "process_create")]
assert [f["id"] for f in analyze(running, "sample.exe", 36060)] == ["LONG_SLEEP"]

print("All behavior_analyzer checks passed.")

#!/usr/bin/env python3
import subprocess
import time
import sys
import os
import selectors

cmd = ["codex", "exec", "只回复 OK, 不要解释, 不要调用工具。"]

start = time.perf_counter()

proc = subprocess.Popen(
    cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    bufsize=0,
    text=False,
)

sel = selectors.DefaultSelector()
sel.register(proc.stdout, selectors.EVENT_READ)
sel.register(proc.stderr, selectors.EVENT_READ)

first_stdout_time = None
stdout_bytes = b""
stderr_bytes = b""

while True:
    events = sel.select(timeout=0.1)

    for key, _ in events:
        data = key.fileobj.read1(4096) if hasattr(key.fileobj, "read1") else key.fileobj.read(4096)
        if not data:
            continue

        if key.fileobj is proc.stdout:
            if first_stdout_time is None:
                first_stdout_time = time.perf_counter()
            stdout_bytes += data
        else:
            stderr_bytes += data

    if proc.poll() is not None:
        # drain remaining output
        if proc.stdout:
            rest = proc.stdout.read()
            if rest:
                if first_stdout_time is None:
                    first_stdout_time = time.perf_counter()
                stdout_bytes += rest
        if proc.stderr:
            rest = proc.stderr.read()
            if rest:
                stderr_bytes += rest
        break

end = time.perf_counter()

print("=" * 60)
print(f"exit_code: {proc.returncode}")
print(f"total_time: {end - start:.3f} s")

if first_stdout_time is not None:
    print(f"1st_token_latency_approx: {first_stdout_time - start:.3f} s")
else:
    print("1st_token_latency_approx: NO_STDOUT_CAPTURED")

print("-" * 60)
print("stdout:")
print(stdout_bytes.decode("utf-8", errors="replace"))
print("-" * 60)
print("stderr:")
print(stderr_bytes.decode("utf-8", errors="replace"))
print("=" * 60)

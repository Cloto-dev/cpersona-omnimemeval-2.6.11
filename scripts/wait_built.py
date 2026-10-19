"""Wait until a CPersona server has built every node and block its stores queued, then check.

usage: <harness python> wait_built.py <settings file> [--fix]

CPersona builds a stored record's nodes and blocks on its task queue, after the store returns, so
a search that follows ingestion at once reads records whose blocks do not exist yet. This waits
for the queue to stay empty for three polls in a row, then asks check_health (report-only, every
agent) for records still missing nodes or blocks; with --fix it repairs those until none are left.
Exit 0 when nothing is missing.
"""
import json, os, re, sys, time
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HARNESS / "scripts"))
for line in open(sys.argv[1]):
    m = re.match(r'^([A-Z_]+)="?(.*?)"?$', line.strip())
    if m:
        os.environ[m.group(1)] = m.group(2)
from client_factory.cpersona_client import CpersonaClient  # noqa: E402

c = CpersonaClient()
quiet, start = 0, time.time()
while quiet < 3:
    pending = c.call("get_queue_status", {}).get("pending")
    quiet = quiet + 1 if pending == 0 else 0
    print(f"{time.strftime('%H:%M:%S')} pending={pending} quiet={quiet}", flush=True)
    time.sleep(60 if pending else 10)
print(f"queue empty after {time.time() - start:.0f}s", flush=True)

checks = ["missing_nodes", "missing_blocks"]
for attempt in range(30):
    issues = c.call("check_health", {"agent_id": "", "checks": checks}).get("issues", [])
    left = {i.get("type"): i.get("count") for i in issues if i.get("type") in checks and i.get("count")}
    print("missing:", left or "none", flush=True)
    if not left:
        sys.exit(0)
    if "--fix" not in sys.argv:
        sys.exit(1)
    c.call("check_health", {"agent_id": "", "checks": checks, "fix": True})
sys.exit(1)

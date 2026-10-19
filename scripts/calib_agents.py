"""Calibrate a CPersona server's gate for each named agent once, so that arms cloned from its store share thresholds.

The server calibrates its global threshold at startup when the store has no sidecar, and an agent's threshold on the
agent's first recall; both sample pairs at random, so two servers on clones of one store end with different
thresholds. Run this against the store before cloning it, then copy its sidecar next to every clone.
usage: <harness python> calib_agents.py <settings file> <agent id> [<agent id> ...]
"""
import os, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
for line in open(sys.argv[1]):
    m = re.match(r'^([A-Z_]+)="?(.*?)"?$', line.strip())
    if m:
        os.environ[m.group(1)] = m.group(2)
from client_factory.cpersona_client import CpersonaClient  # noqa: E402

c = CpersonaClient()
for agent in sys.argv[2:]:
    res = c.call("calibrate_threshold", {"agent_id": agent})
    print(agent, {k: res.get(k) for k in ("threshold", "previous", "method", "pairs", "persisted") if k in res} or str(res)[:200], flush=True)

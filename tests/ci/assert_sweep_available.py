"""Read a `harvest.py sweep --json` payload on stdin and fail unless the process and socket steps
both ran. The Windows CI leg pipes the live sweep into this: the unit suite only proves the parsers
against documented output, and this is the one place the two Windows commands execute for real.
"""

# The payload is whatever the script printed, so it is Any by construction — the same suppression
# the unit tests carry for the scripts they load by path.
# pyright: reportAny=false, reportExplicitAny=false

import json
import sys
from typing import Any


def main() -> int:
    payload: dict[str, Any] = json.load(sys.stdin)
    problems: list[str] = []
    for section in ("processes", "sockets"):
        state: dict[str, Any] = payload.get(section, {})
        if not state.get("available"):
            problems.append(f"{section}: unavailable — {state.get('why', 'no reason given')}")
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    procs: dict[str, Any] = payload["processes"]
    socks: dict[str, Any] = payload["sockets"]
    children: list[Any] = procs.get("session_children", [])
    watchers: list[Any] = procs.get("watchers_and_servers", [])
    listeners: list[Any] = socks.get("listeners", [])
    exposed: list[Any] = socks.get("exposed", [])
    print(
        f"processes: harness pid {procs.get('harness_pid')}, {len(children)} children, "
        f"{len(watchers)} watchers/servers; sockets: {len(listeners)} listeners, {len(exposed)} exposed"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

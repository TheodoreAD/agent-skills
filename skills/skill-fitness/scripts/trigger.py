#!/usr/bin/env python3
"""Ask which skill a cold request actually selects, by running the request.

The static analyzer (`fitness.py overlap`) says which pairs *look* like they compete. Only a live
run says which one wins. This is that run, and it is the only part of this skill that costs tokens.

Two modes, and the difference matters:

    run        real installed skills, real descriptions. "A request meant for B — what fired?"
               This is the contention measurement, and it needs no synthetic anything: the
               installed set is already the thing under test.

    candidate  a *proposed* description, not yet adopted, tested the way Anthropic's own
               skill-creator does it — written to a temporary command file so it joins the listing
               alongside the real skills, then scored against the same cases. This is the measure
               half of "draft, measure, decide" and the reason a drafted description is allowed at
               all: SkillsBench found unmeasured model-authored skills scoring below having no
               skill (-1.3pp), which is an argument against shipping unmeasured, not against
               drafting.

Selection is all that is measured. The run is killed the moment a skill is named, so a case never
proceeds into the skill's actual work — which also means a trigger case for a skill whose commands
enumerate private directories can never print them.

Cases are JSON. The plan for this skill originally chose `case.yaml`, to match the format Claude
Code's own (still early-access) eval runner consumes; that was reversed here because this family's
skills are stdlib-only, and hand-rolling a YAML parser for prompts full of colons is precisely the
ad-hoc-script pattern `fitness.py absorb` exists to find. Converting is mechanical once that runner
is usable.

    {
      "cases": [
        {"prompt": "how do I name a new invoke task?", "expect": "invoke-task-conventions"},
        {"prompt": "what is the capital of France?", "expect": null}
      ]
    }

`expect: null` is a should-not-trigger case, and a suite without several of them measures nothing:
a description that fires on everything passes every positive case.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import select
import subprocess
import sys
import tempfile
import time
import uuid
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

STREAM_ARGS = ["--output-format", "stream-json", "--verbose", "--include-partial-messages"]


@dataclass
class Result:
    prompt: str
    expect: str | None
    fired: list[str | None]
    # In candidate mode the proposed description is installed *alongside* the real skill it is a
    # proposal for, so both names satisfy the same case. Scoring them as different skills reports
    # a failure every time the incumbent wins, which is not a failure — it is the same skill.
    # Confirmed 2026-08-31 on this suite's first candidate run: two cases "failed" that way while
    # the case the candidate was written to fix passed 3/3.
    equivalent: frozenset[str] = frozenset()

    def _wanted(self) -> frozenset[str]:
        if self.expect is None:
            return frozenset()
        return self.equivalent if self.expect in self.equivalent else frozenset({self.expect})

    @property
    def rate(self) -> float:
        want = self._wanted()
        hits = sum(1 for f in self.fired if (f in want if want else f is None))
        return hits / len(self.fired) if self.fired else 0.0

    @property
    def passed(self) -> bool:
        return self.rate > 0.5


class _Undecided:
    """Sentinel: this line settled nothing. Distinct from None, which means 'no skill fired'."""


_UNDECIDED = _Undecided()


class _StreamState:
    """Decides, line by line, which skill a run selected.

    Split out of `run_query` because the loop underneath it is I/O plumbing and this is the actual
    protocol: the first `tool_use` block wins. If it is `Skill`, the name arrives piecemeal in
    `input_json_delta` fragments and has to be accumulated; if it is any other tool, the model chose
    to do the work directly and no skill was selected.
    """

    def __init__(self) -> None:
        self.pending = False
        self.accumulated = ""

    def feed(self, line: str) -> str | _Undecided | None:
        if not line.strip():
            return _UNDECIDED
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            return _UNDECIDED
        if event.get("type") != "stream_event":
            return _UNDECIDED

        se = event.get("event", {})
        kind = se.get("type")
        if kind == "content_block_start":
            block = se.get("content_block", {})
            if block.get("type") != "tool_use":
                return _UNDECIDED
            if block.get("name") == "Skill":
                self.pending, self.accumulated = True, ""
                return _UNDECIDED
            # Another tool started first: nothing was selected. Stop paying for the run.
            return None
        if kind == "content_block_delta" and self.pending:
            delta = se.get("delta", {})
            if delta.get("type") == "input_json_delta":
                self.accumulated += delta.get("partial_json", "")
                m = re.search(r'"skill"\s*:\s*"([^"]+)"', self.accumulated)
                if m:
                    return m.group(1)
        return _UNDECIDED


def run_query(prompt: str, cwd: Path, timeout: int, model: str | None) -> str | None:
    """Run one cold request; return the skill name that fired, or None.

    Detection reads the *streamed* tool_use block rather than waiting for the finished message,
    because the finished message only arrives after the tool has run — and the whole point is to
    stop before that.
    """
    cmd = ["claude", "-p", prompt, *STREAM_ARGS]
    if model:
        cmd += ["--model", model]

    # CLAUDECODE is a guard against interactive nesting; a programmatic subprocess is not that, and
    # leaving it set makes the child refuse to start when this is run from inside a session.
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, cwd=str(cwd), env=env)
    state = _StreamState()
    buffer = ""
    deadline = time.time() + timeout

    try:
        assert proc.stdout is not None
        while time.time() < deadline:
            if proc.poll() is not None:
                buffer += proc.stdout.read().decode("utf-8", errors="replace")
                break
            ready, _, _ = select.select([proc.stdout], [], [], 1.0)
            if not ready:
                continue
            chunk = os.read(proc.stdout.fileno(), 8192)
            if not chunk:
                break
            buffer += chunk.decode("utf-8", errors="replace")

            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                verdict = state.feed(line)
                if verdict is not _UNDECIDED:
                    return verdict
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
    return None


def write_candidate(root: Path, name: str, description: str) -> str:
    """Put a proposed description into the listing under a unique name, as a command file."""
    unique = f"{name}-candidate-{uuid.uuid4().hex[:8]}"
    commands = root / ".claude" / "commands"
    commands.mkdir(parents=True, exist_ok=True)
    indented = "\n  ".join(description.splitlines())
    (commands / f"{unique}.md").write_text(
        f"---\ndescription: |\n  {indented}\n---\n\n# {unique}\n\n{description}\n",
        encoding="utf-8",
    )
    return unique


def write_proposal(root: Path, proposal: dict[str, Any]) -> dict[str, str]:
    """Register every skill in a proposed split at once, and map proposed name to registered name.

    Testing a split one description at a time cannot answer the question a split actually raises,
    which is how requests *distribute* across the pieces. They have to compete simultaneously, and
    against the incumbent, which is still installed.
    """
    mapping: dict[str, str] = {}
    for skill in proposal["skills"]:
        mapping[skill["name"]] = write_candidate(root, skill["name"], skill["description"])
    return mapping


def load_cases(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    cases = data["cases"] if isinstance(data, dict) else data
    if not isinstance(cases, list) or not cases:
        raise SystemExit(f"{path}: no cases found")
    return cases


def summarise(results: list[Result], collapse: dict[str, str] | None = None) -> dict[str, Any]:
    """Per-skill precision and recall, plus who actually won the cases it lost.

    `collapse` folds a candidate name onto the skill it is a proposal for. Without it the table
    reports the incumbent at precision 0.0 while the case-level verdict says every case passed —
    two true statements that read as a contradiction, which is worse than either alone.
    """
    collapse = collapse or {}

    def fold(name: str | None) -> str | None:
        return collapse.get(name, name) if name else name

    per_skill: dict[str, dict[str, int]] = {}
    for raw in results:
        r = Result(
            prompt=raw.prompt,
            expect=fold(raw.expect),
            fired=[fold(f) for f in raw.fired],
            equivalent=raw.equivalent,
        )
        for f in r.fired:
            if r.expect:
                per_skill.setdefault(r.expect, {"tp": 0, "fn": 0, "fp": 0})
            if f:
                per_skill.setdefault(f, {"tp": 0, "fn": 0, "fp": 0})
            if r.expect and f == r.expect:
                per_skill[r.expect]["tp"] += 1
            else:
                if r.expect:
                    per_skill[r.expect]["fn"] += 1
                if f:
                    per_skill[f]["fp"] += 1

    rows = []
    for name, c in sorted(per_skill.items()):
        precision = c["tp"] / (c["tp"] + c["fp"]) if (c["tp"] + c["fp"]) else 1.0
        recall = c["tp"] / (c["tp"] + c["fn"]) if (c["tp"] + c["fn"]) else 1.0
        rows.append(
            {
                "skill": name,
                "tp": c["tp"],
                "fp": c["fp"],
                "fn": c["fn"],
                "precision": round(precision, 2),
                "recall": round(recall, 2),
            }
        )
    return {"per_skill": rows}


def execute(
    cases: list[dict[str, Any]], args: argparse.Namespace
) -> tuple[list[Result], frozenset[str], dict[str, str]]:
    """Run every case in a scratch project, so only globally installed skills are in the listing."""
    with tempfile.TemporaryDirectory(prefix="skill-trigger-") as tmp:
        root = Path(tmp)
        expect_override: str | None = None
        remap: dict[str, str] = {}

        incumbent_twins: frozenset[str] = frozenset()
        if args.mode == "split":
            proposal = json.loads(Path(args.proposal).read_text(encoding="utf-8"))
            remap = write_proposal(root, proposal)
            for proposed, registered in remap.items():
                print(f"proposed {proposed} registered as {registered}", file=sys.stderr)
            replaces = proposal.get("replaces")
            print(f"incumbent still installed: {replaces}", file=sys.stderr)
            # A split usually keeps the original name for the piece that inherits the core, so that
            # piece and the still-installed incumbent are the same skill under two names — the same
            # twin problem candidate mode already has, and it has to be scored the same way.
            if replaces in remap:
                incumbent_twins = frozenset({replaces, remap[replaces]})
        elif args.mode == "candidate":
            if not args.skill or not args.description:
                raise SystemExit("candidate mode needs --skill and --description")
            desc = args.description
            if desc.startswith("@"):
                desc = Path(desc[1:]).read_text(encoding="utf-8").strip()
            expect_override = write_candidate(root, args.skill, desc)
            remap = {args.skill: expect_override}
            print(f"candidate registered as {expect_override}", file=sys.stderr)

        twins = incumbent_twins or (
            frozenset({expect_override, args.skill}) if expect_override and args.skill else frozenset()
        )

        results: list[Result] = []
        for i, case in enumerate(cases, 1):
            expect = case.get("expect")
            if expect in remap:
                expect = remap[expect]
            fired: list[str | None] = [
                run_query(str(case["prompt"]), root, args.timeout, args.model) for _ in range(args.runs)
            ]
            r = Result(prompt=str(case["prompt"]), expect=expect, fired=fired, equivalent=twins)
            results.append(r)
            mark = "ok  " if r.passed else "FAIL"
            got = Counter(f or "(none)" for f in fired)
            got_text = ", ".join(f"{k}x{v}" for k, v in got.most_common())
            print(f"  [{i}/{len(cases)}] {mark} want={expect or '(none)'} got={got_text}", file=sys.stderr)

    return results, twins, remap


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("mode", choices=["run", "candidate", "split"])
    p.add_argument("cases", type=Path, help="a JSON file of cases")
    p.add_argument("--runs", type=int, default=3, help="repeats per case; selection is not deterministic")
    p.add_argument("--timeout", type=int, default=90, help="seconds per run")
    p.add_argument("--model", default=None, help="override the model used for the probe")
    p.add_argument("--skill", help="candidate mode: the skill name the proposed description is for")
    p.add_argument("--description", help="candidate mode: the proposed description, or @<file>")
    p.add_argument("--proposal", help="split mode: JSON with `replaces` and a list of proposed skills")
    p.add_argument("--json", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="print what would run, spend nothing")
    args = p.parse_args()

    cases = load_cases(args.cases)
    total_runs = len(cases) * args.runs
    if args.dry_run:
        print(f"{len(cases)} cases x {args.runs} runs = {total_runs} agent runs")
        for c in cases:
            print(f"  expect={c.get('expect')!r:32} {c['prompt'][:90]}")
        return 0

    results, _twins, remap = execute(cases, args)
    passed = sum(1 for r in results if r.passed)
    out: dict[str, Any] = {
        "cases": len(results),
        "passed": passed,
        "runs_per_case": args.runs,
        "results": [
            {"prompt": r.prompt, "expect": r.expect, "fired": r.fired, "rate": round(r.rate, 2)} for r in results
        ],
        # Fold every registered candidate name back onto the name it is a proposal for, so the
        # table reads in the names the author chose rather than in generated ones.
        **summarise(results, {registered: proposed for proposed, registered in remap.items()}),
    }

    if args.json:
        print(json.dumps(out, indent=2))
        return 0 if passed == len(results) else 1

    print(f"\n{passed}/{len(results)} cases passed at {args.runs} runs each")
    for row in out["per_skill"]:
        print(
            f"  {row['skill']:34s} precision={row['precision']:<5} recall={row['recall']:<5} "
            f"tp={row['tp']} fp={row['fp']} fn={row['fn']}"
        )

    if args.mode == "split":
        proposal = json.loads(Path(args.proposal).read_text(encoding="utf-8"))
        incumbent = proposal.get("replaces")
        fires = Counter(f for r in results for f in r.fired if f)
        reverse = {v: k for k, v in remap.items()}
        print("\n  where the requests went:")
        for name, n in fires.most_common():
            label = reverse.get(name, name)
            note = "  <- INCUMBENT, not the split" if name == incumbent else ""
            print(f"    {n:3d}  {label}{note}")
        if fires.get(incumbent):
            print(f"\n  {incumbent} is still installed and won some cases. That is not automatically")
            print("  wrong — it means those requests match the old wording at least as well, and a")
            print("  split has to earn each one. Read it per case rather than in aggregate.")

    if args.mode == "candidate" and args.skill:
        fires = Counter(f for r in results for f in r.fired if f)
        new = sum(v for k, v in fires.items() if k.startswith(f"{args.skill}-candidate-"))
        old = fires.get(args.skill, 0)
        print(f"\n  candidate won {new} of {new + old} fires for this skill; incumbent won {old}")
        print("  Both names satisfy the same case — the split says which wording the model prefers,")
        print("  and a candidate that never wins is not more attractive than what is already there.")

    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

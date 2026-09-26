"""Re-measure --body quality since the flag shipped: length and whether an alternative is named."""

import re
import statistics
import subprocess
from pathlib import Path

ROOTS = [*sorted(Path.home().glob("projects/github.com-personal/*")), Path.home() / "plans"]
SINCE = "2026-09-22T17:00:00+03:00"  # after 6f3e22c renamed the flag to --body
MINE = {"9f84361", "6124990", "57dd9b8", "8380c23", "183ef16", "b3f9819", "48ec225"}
# Subjects plans.py derives; a hand-written -m does not produce these shapes.
DERIVED = re.compile(r"^[\w.-]+: (.+ is now [\w-]+|.+ opens \d|.+ closes \d|retire |\d+ plans are now|absorbed )")
ALTERNATIVE = re.compile(r"\b(beat|instead|rather than|over |rejected|alternative|versus|vs\.?|than )", re.IGNORECASE)

rows = []
for repo in ROOTS:
    if not (repo / ".git").exists():
        continue
    out = subprocess.run(
        ["git", "-C", str(repo), "log", f"--since={SINCE}", "--format=%x1e%h%x1f%s%x1f%b", "--", "."],
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    for record in out.split("\x1e")[1:]:
        sha, subject, body = [*record.split("\x1f"), "", ""][:3]
        if not DERIVED.match(subject) or sha[:7] in MINE:
            continue
        body = "\n".join(line for line in body.strip().splitlines() if not re.match(r"^[\w-]+: .+@", line)).strip()
        rows.append((repo.name, sha[:7], subject[:70], len(body), bool(ALTERNATIVE.search(body))))

for row in rows:
    print(*row, sep="  ")
lengths = [r[3] for r in rows if r[3]]
print(f"\n{len(rows)} derived-subject commits; {len(lengths)} with a body; {sum(1 for r in rows if not r[3])} bare")
if lengths:
    print(f"body length median {statistics.median(lengths):.0f}, min {min(lengths)}, max {max(lengths)}")
    print(f"naming an alternative: {sum(1 for r in rows if r[3] and r[4])} of {len(lengths)}")

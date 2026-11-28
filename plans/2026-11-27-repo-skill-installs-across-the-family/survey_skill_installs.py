"""Survey each repo under a root: authored skills against installed copies, and the gitignore.

Usage: python3 survey_skill_installs.py [ROOT]
(default ~/projects/personal; repos sit directly under it)

Per repo it prints the authored skills (skills/<name>/SKILL.md), whether repo-tasks' invoke tasks
are present, what .agents/skills/ and .claude/skills/ hold (dir, junction, symlink), the lock
file's entries, whether each of the three install targets is gitignored and whether any is tracked,
then per skill: current, STALE (installed copy differs from source) or NOT INSTALLED. Read-only.
"""

import filecmp
import json
import subprocess
import sys
from pathlib import Path

TARGETS = (".agents/skills", ".claude/skills", "skills-lock.json")


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    # check=False: check-ignore exits 1 for "not ignored", which is an answer, not a failure.
    cmd = ["git", "-C", str(repo), *args]
    return subprocess.run(cmd, check=False, capture_output=True, text=True)


def kind(path: Path) -> str:
    if getattr(path, "is_junction", lambda: False)():
        return "junction"
    if path.is_symlink():
        return "symlink"
    return "dir" if path.is_dir() else "file"


def same_tree(a: Path, b: Path) -> bool:
    cmp = filecmp.dircmp(a, b)
    if cmp.left_only or cmp.right_only or cmp.diff_files or cmp.funny_files:
        return False
    return all(same_tree(a / d, b / d) for d in cmp.common_dirs)


def uses_repo_tasks(repo: Path) -> bool:
    files = []
    for t in (repo / "tasks.py", repo / "tasks"):
        if t.is_file():
            files.append(t)
        elif t.is_dir():
            files.extend(t.rglob("*.py"))
    return any("repo_tasks" in f.read_text(encoding="utf-8", errors="ignore") for f in files)


def survey(repo: Path) -> None:
    authored = sorted(p.parent.name for p in (repo / "skills").glob("*/SKILL.md"))
    agents, claude = repo / ".agents" / "skills", repo / ".claude" / "skills"
    installed = sorted(p.name for p in agents.iterdir()) if agents.is_dir() else []
    linked = {p.name: kind(p) for p in claude.iterdir()} if claude.is_dir() else {}
    lock = repo / "skills-lock.json"
    locked = sorted(json.loads(lock.read_text(encoding="utf-8")).get("skills", {})) if lock.exists() else []
    ignored = "/".join("y" if git(repo, "check-ignore", "-q", t).returncode == 0 else "n" for t in TARGETS)
    tracked = len(git(repo, "ls-files", *TARGETS).stdout.split())
    print(f"== {repo.name}")
    print(f"   repo-tasks: {'yes' if uses_repo_tasks(repo) else 'no'}   ignored a/c/l: {ignored}   tracked: {tracked}")
    print(f"   authored: {authored}")
    print(f"   .agents/skills: {installed}")
    print(f"   .claude/skills: {linked}")
    print(f"   lock: {locked}")
    for skill in authored:
        if skill not in installed:
            state = "NOT INSTALLED"
        else:
            state = "current" if same_tree(repo / "skills" / skill, agents / skill) else "STALE"
        if skill in installed and skill not in linked:
            state += ", no .claude/skills entry"
        print(f"   {skill}: {state}")
    for skill in installed:
        if skill not in authored:
            print(f"   {skill}: installed but not authored here")


def main() -> None:
    root = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else Path.home() / "projects" / "personal"
    for repo in sorted(p.parent for p in root.glob("*/.git")):
        survey(repo)


if __name__ == "__main__":
    main()

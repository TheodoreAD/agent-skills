"""Dogfoods the same quality tasks every template consumer gets — see README.md.

repo_tasks is deliberately not a project dependency (only the globally `uv tool install`ed
repo-tasks makes it resolvable) — invisible to a type checker that only sees this project's own
venv, hence the pyright suppressions below: the import can't resolve, so `ns` can't be typed."""

from repo_tasks import ns  # pyright: ignore[reportMissingImports, reportUnknownVariableType]

__all__ = ["ns"]

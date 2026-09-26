#!/usr/bin/env bash
# The lowest interpreter each skill script compiles under, and which version-gated stdlib names it
# imports. Compilation is the syntax floor only -- a script that compiles under 3.9 still fails at
# import time on `import tomllib`, so the second half is not optional.
set -uo pipefail

SKILLS=/home/tdumitrescu/projects/github.com-personal/agent-skills/skills
BIN=/home/tdumitrescu/.local/share/uv/python

py() { # py <minor> -> path to that interpreter
  echo "$BIN/cpython-3.$1-linux-x86_64-gnu/bin/python3.$1"
}

printf '%-46s %s\n' "script" "lowest syntax  version-gated stdlib"
for script in "$SKILLS"/*/scripts/*.py; do
  rel="${script#"$SKILLS"/}"
  lowest="none"
  for minor in 9 10 11 12 13; do
    if "$(py "$minor")" -m py_compile "$script" 2> /dev/null; then
      lowest="3.$minor"
      break
    fi
  done
  gated=$(rg -o --no-filename \
    'import tomllib|contextlib\.chdir|datetime\.UTC|\bStrEnum\b|itertools\.batched|typing import Self|typing import override|ExceptionGroup|asyncio\.TaskGroup|\bdatetime\.UTC\b' \
    "$script" | sort -u | paste -sd, -)
  printf '%-46s %-14s %s\n' "$rel" "$lowest" "${gated:--}"
done

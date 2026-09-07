"""Every attribute assignment in a module, so 'is this record ever mutated' is a measurement.

python3 find_mutations.py <module.py> [<module.py> ...]
"""

import argparse
import ast
from pathlib import Path


def mutations(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: list[str] = []
    for node in ast.walk(tree):
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            targets = list(node.targets)
        elif isinstance(node, ast.AugAssign | ast.AnnAssign):
            targets = [node.target]
        found += [f"{node.lineno}: {ast.unparse(t)} = ..." for t in targets if isinstance(t, ast.Attribute)]
    return found


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("module", type=Path, nargs="+", help="the module(s) to list attribute assignments in")
    modules = ap.parse_args().module
    for path in modules:
        if len(modules) > 1:
            print(f"\n=== {path}")
        for line in mutations(path):
            print(line)


if __name__ == "__main__":
    main()

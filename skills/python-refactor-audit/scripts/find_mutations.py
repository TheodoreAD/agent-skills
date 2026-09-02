"""Every attribute assignment in a module, so 'is this record ever mutated' is a measurement."""

import ast
import sys
from pathlib import Path

path = Path(sys.argv[1])
tree = ast.parse(path.read_text(encoding="utf-8"))

for node in ast.walk(tree):
    targets: list[ast.expr] = []
    if isinstance(node, ast.Assign):
        targets = list(node.targets)
    elif isinstance(node, ast.AugAssign | ast.AnnAssign):
        targets = [node.target]
    for target in targets:
        if isinstance(target, ast.Attribute):
            print(f"{node.lineno}: {ast.unparse(target)} = ...")

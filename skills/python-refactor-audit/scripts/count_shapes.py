"""Count anonymous record shapes in a module: parameters as well as returns.

The pilot measured returns only, which is how a tuple parameter survived the pass unseen.
"""

import ast
import sys
from pathlib import Path


def anon_tuple(node: ast.expr | None) -> bool:
    """True for tuple[...] / list[tuple[...]] annotations with more than one distinct element type."""
    if node is None:
        return False
    if isinstance(node, ast.Subscript):
        base = ast.unparse(node.value)
        if base in {"tuple", "Tuple"}:
            inner = node.slice
            if isinstance(inner, ast.Tuple):
                parts = [ast.unparse(e) for e in inner.elts]
                # tuple[str, ...] is a homogeneous collection, not a record
                return "Ellipsis" not in parts and "..." not in parts
            return False
        if base in {"list", "List", "Sequence", "Iterable", "Iterator"}:
            return anon_tuple(node.slice)
    return False


def dict_annotation(node: ast.expr | None) -> bool:
    if node is None or not isinstance(node, ast.Subscript):
        return False
    return ast.unparse(node.value) in {"dict", "Dict", "Mapping", "MutableMapping"}


def main() -> None:
    path = Path(sys.argv[1])
    tree = ast.parse(path.read_text(encoding="utf-8"))

    ret_hits: list[str] = []
    param_hits: list[str] = []
    dict_param_hits: list[str] = []
    dict_field_hits: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            if anon_tuple(node.returns):
                ret_hits.append(f"{node.name} -> {ast.unparse(node.returns)}")
            args = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
            for arg in args:
                if anon_tuple(arg.annotation):
                    param_hits.append(f"{node.name}({arg.arg}: {ast.unparse(arg.annotation)})")
                elif dict_annotation(arg.annotation):
                    dict_param_hits.append(f"{node.name}({arg.arg}: {ast.unparse(arg.annotation)})")
        elif isinstance(node, ast.AnnAssign) and dict_annotation(node.annotation):
            dict_field_hits.append(f"{ast.unparse(node.target)}: {ast.unparse(node.annotation)}")

    for label, hits in (
        ("anonymous tuple RETURNS", ret_hits),
        ("anonymous tuple PARAMETERS", param_hits),
        ("dict parameters", dict_param_hits),
        ("dict fields/annotated assignments", dict_field_hits),
    ):
        print(f"\n{label}: {len(hits)}")
        for hit in hits:
            print(f"  {hit}")


if __name__ == "__main__":
    main()

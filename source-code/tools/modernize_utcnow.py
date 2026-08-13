"""Replace deprecated ``datetime.utcnow`` calls throughout the application."""

import argparse
import ast
from pathlib import Path


DEPRECATED = "datetime.utcnow"
REPLACEMENT = "legacy_utc_now"
IMPORT = "from app.time_utils import legacy_utc_now"


def insertion_index(source):
    """Return a zero-based line index after the module's import section."""

    tree = ast.parse(source)
    body = list(tree.body)
    position = 0

    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        position = body.pop(0).end_lineno

    for node in body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            position = node.end_lineno
            continue
        break

    return position


def transformed(source):
    """Return source using the shared compatibility-safe UTC helper."""

    updated = source.replace(DEPRECATED, REPLACEMENT)
    if IMPORT not in updated:
        lines = updated.splitlines(keepends=True)
        position = insertion_index(updated)
        lines.insert(position, f"{IMPORT}\n")
        updated = "".join(lines)

    ast.parse(updated)
    return updated


def affected_files(root):
    """Yield application Python files that still use deprecated UTC calls."""

    for path in sorted((root / "app").rglob("*.py")):
        if path.name == "time_utils.py":
            continue
        if DEPRECATED in path.read_text(encoding="utf-8"):
            yield path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write the modernization changes; otherwise only report them.",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    paths = list(affected_files(root))

    if not paths:
        print("No deprecated datetime.utcnow references found.")
        return 0

    for path in paths:
        relative = path.relative_to(root)
        if args.apply:
            source = path.read_text(encoding="utf-8")
            path.write_text(transformed(source), encoding="utf-8")
            print(f"updated {relative}")
        else:
            print(f"would update {relative}")

    if not args.apply:
        print(f"{len(paths)} files require modernization; rerun with --apply.")
    else:
        print(f"Modernized {len(paths)} files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.14"
# ///
"""Verify HTML tools include the local analytics snippet."""

from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check that HTML tools include /analytics.js"
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Optional HTML tool files to check (defaults to all tools)",
    )
    return parser.parse_args()


def iter_tool_files(repo_root: Path) -> list[Path]:
    tools_root = repo_root / "content" / "tools" / "html"
    if not tools_root.exists():
        return []
    return sorted(tools_root.rglob("tool.html"))


def has_analytics_snippet(text: str) -> bool:
    return "/analytics.js" in text


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]

    tool_files = [path for path in args.paths if path.suffix == ".html"]
    if not tool_files:
        tool_files = iter_tool_files(repo_root)

    missing: list[str] = []
    for tool_path in tool_files:
        resolved = (
            (repo_root / tool_path).resolve()
            if not tool_path.is_absolute()
            else tool_path
        )
        if not resolved.exists():
            continue
        content = resolved.read_text(encoding="utf-8")
        if not has_analytics_snippet(content):
            missing.append(str(resolved.relative_to(repo_root)))

    if missing:
        print("Missing analytics snippet in:")
        for path in missing:
            print(f"- {path}")
        print('Add: <script src="/analytics.js"></script> before </body>.')
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

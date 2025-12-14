#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.14"
# dependencies = [
#   "PyYAML>=6.0.0",
# ]
# ///
"""Detect added, updated, or removed tool entries in data/tools.yaml."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from typing import Any, Dict, List

import yaml


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize changes in data/tools.yaml")
    parser.add_argument(
        "path",
        type=Path,
        nargs="?",
        default=Path("data/tools.yaml"),
        help="Path to tools.yaml (default: data/tools.yaml)",
    )
    return parser.parse_args()


def read_head_version(path: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "show", f"HEAD:{path.as_posix()}"], text=True
        )
    except subprocess.CalledProcessError:
        return ""


def load_yaml_entries(content: str) -> Dict[str, Any]:
    if not content.strip():
        return {}
    loaded = yaml.safe_load(content) or {}
    tools = loaded.get("tools", []) if isinstance(loaded, dict) else []
    entries: Dict[str, Any] = {}
    for entry in tools:
        if not isinstance(entry, dict):
            continue
        for slug, data in entry.items():
            entries[str(slug)] = data
    return entries


def summarize_changes(
    head_entries: Dict[str, Any], worktree_entries: Dict[str, Any]
) -> str:
    head_slugs = set(head_entries)
    worktree_slugs = set(worktree_entries)

    added = sorted(worktree_slugs - head_slugs)
    removed = sorted(head_slugs - worktree_slugs)
    updated: List[str] = []
    for slug in sorted(head_slugs & worktree_slugs):
        if head_entries[slug] != worktree_entries[slug]:
            updated.append(slug)

    parts: List[str] = []
    if added:
        parts.append("added " + ", ".join(added))
    if updated:
        parts.append("updated " + ", ".join(updated))
    if removed:
        parts.append("removed " + ", ".join(removed))
    return "; ".join(parts)


def main() -> int:
    args = parse_args()
    target = args.path

    head_content = read_head_version(target)
    worktree_content = target.read_text(encoding="utf-8") if target.exists() else ""

    head_entries = load_yaml_entries(head_content)
    worktree_entries = load_yaml_entries(worktree_content)

    summary = summarize_changes(head_entries, worktree_entries)
    if summary:
        print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

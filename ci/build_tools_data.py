#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.14"
# dependencies = [
#   "structlog>=24.0.0",
#   "PyYAML>=6.0.0",
# ]
# ///
"""Build `data/tools.yaml` by walking `content/tools/**/index.md`.

Rules (see PROBLEM.md):
- Each `content/tools/**/index.md` is considered a tool entry unless:
  - it has `draft: true`, or
  - front matter contains `toolbox.ignore: true`
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

try:
    import structlog
except (
    ModuleNotFoundError
) as exc:  # pragma: no cover - dependency should be installed in CI
    raise SystemExit(
        "Missing dependency 'structlog'. "
        "Install it (e.g. `pip install structlog`) or run via a PEP-723 aware runner (e.g. `uv run`)."
    ) from exc

try:
    import yaml
except (
    ModuleNotFoundError
) as exc:  # pragma: no cover - dependency should be installed in CI
    raise SystemExit(
        "Missing dependency 'PyYAML'. "
        "Install it (e.g. `pip install pyyaml`) or run via a PEP-723 aware runner (e.g. `uv run`)."
    ) from exc


class FrontMatterError(ValueError):
    pass


def _configure_logging() -> structlog.stdlib.BoundLogger:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    return structlog.get_logger("ci.build_tools_data")


def _run_git(args: list[str], *, cwd: Path) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def _get_tool_git_commits(tool_dir: Path) -> tuple[str | None, str | None]:
    """Return (introduced_commit, updated_commit) for the tool directory.

    If there is no git history, returns (None, None).
    If the most recent commit matches the introduction commit, updated_commit is None.
    """

    repo_root = Path(__file__).resolve().parents[1]
    rel_path = tool_dir.relative_to(repo_root)

    try:
        first_commit = _run_git(
            ["log", "--reverse", "--format=%H", "--", str(rel_path)],
            cwd=repo_root,
        ).splitlines()
        if not first_commit:
            return None, None
        introduced_commit = first_commit[0].strip() or None

        latest_commit = (
            _run_git(
                ["log", "-n", "1", "--format=%H", "--", str(rel_path)],
                cwd=repo_root,
            ).strip()
            or None
        )
    except Exception:
        logger = structlog.get_logger("ci.build_tools_data")
        logger.exception("git history lookup failed", tool_dir=str(rel_path))
        return None, None

    if introduced_commit and latest_commit and introduced_commit != latest_commit:
        return introduced_commit, latest_commit
    return introduced_commit, None


def _extract_front_matter(md_text: str) -> dict[str, Any]:
    lines = md_text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}

    end = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end = idx
            break
    if end is None:
        raise FrontMatterError(
            "Front matter starts with '---' but no closing '---' found."
        )

    block = "\n".join(lines[1:end]).strip("\n")
    if not block.strip():
        return {}

    try:
        data = yaml.safe_load(block)
    except yaml.YAMLError as exc:
        raise FrontMatterError("Front matter YAML failed to parse.") from exc

    if data is None:
        return {}
    if not isinstance(data, dict):
        raise FrontMatterError("Front matter YAML must be a mapping.")
    return data


def _yaml_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


@dataclass(frozen=True)
class ToolEntry:
    slug: str
    title: str
    language: str
    description: str
    toolbox_file: str
    introduced_commit: str | None
    updated_commit: str | None
    tags: tuple[str, ...]


def _iter_tool_index_files(tools_root: Path) -> Iterable[Path]:
    yield from sorted(tools_root.rglob("index.md"))


def _coerce_tags(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (list, tuple)):
        return tuple(str(item) for item in value if str(item).strip())
    if isinstance(value, str) and value.strip():
        return (value.strip(),)
    return ()


def _build_tool_entry(index_md: Path, *, tools_root: Path) -> ToolEntry | None:
    fm = _extract_front_matter(index_md.read_text(encoding="utf-8"))
    if fm.get("draft") is True:
        return None

    toolbox: dict[str, Any] = {}
    if isinstance(fm.get("toolbox"), dict):
        toolbox = fm["toolbox"]
    elif isinstance(fm.get("tool"), dict):
        toolbox = fm["tool"]

    if toolbox.get("ignore") is True:
        return None

    rel_dir = index_md.parent.relative_to(tools_root)
    slug = rel_dir.as_posix()
    language = rel_dir.parts[0] if rel_dir.parts else ""

    title = str(fm.get("title") or "")
    description = str(fm.get("description") or "")

    toolbox_file = str(toolbox.get("file") or "tool.html")
    resources = fm.get("resources")
    if isinstance(resources, list):
        for item in resources:
            if not isinstance(item, dict):
                continue
            if item.get("name") == "tool-file" and item.get("src"):
                toolbox_file = str(item["src"])
                break
    tags = _coerce_tags(fm.get("tags"))

    introduced_commit, updated_commit = _get_tool_git_commits(index_md.parent)

    return ToolEntry(
        slug=slug,
        title=title,
        language=language,
        description=description,
        toolbox_file=toolbox_file,
        introduced_commit=introduced_commit,
        updated_commit=updated_commit,
        tags=tags,
    )


def _render_tools_yaml(entries: list[ToolEntry]) -> str:
    lines: list[str] = ["---", "version: 1"]

    if not entries:
        lines.append("tools: []")
        return "\n".join(lines) + "\n"

    lines.append("tools:")
    for entry in entries:
        lines.append(f"  - {entry.slug}:")
        lines.append(f"      title: {_yaml_quote(entry.title)}")
        lines.append(f"      language: {_yaml_quote(entry.language)}")
        lines.append(f"      description: {_yaml_quote(entry.description)}")
        lines.append("      toolbox:")
        lines.append(f"        file: {_yaml_quote(entry.toolbox_file)}")
        lines.append(
            "        introduced_commit: "
            + (
                _yaml_quote(entry.introduced_commit)
                if entry.introduced_commit
                else "null"
            )
        )
        lines.append(
            "        updated_commit: "
            + (_yaml_quote(entry.updated_commit) if entry.updated_commit else "null")
        )
        if entry.tags:
            lines.append("      tags:")
            for tag in entry.tags:
                lines.append(f"        - {_yaml_quote(tag)}")

    return "\n".join(lines) + "\n"


def build_tools_yaml(*, repo_root: Path) -> str:
    tools_root = repo_root / "content" / "tools"
    entries: list[ToolEntry] = []
    for index_md in _iter_tool_index_files(tools_root):
        entry = _build_tool_entry(index_md, tools_root=tools_root)
        if entry is not None:
            entries.append(entry)

    entries.sort(key=lambda e: e.slug)
    return _render_tools_yaml(entries)


def main() -> int:
    log = _configure_logging()
    repo_root = Path(__file__).resolve().parents[1]
    tools_root = repo_root / "content" / "tools"
    out_path = repo_root / "data" / "tools.yaml"

    log.info("building tools data", tools_root=tools_root)
    try:
        yaml_text = build_tools_yaml(repo_root=repo_root)
    except Exception:
        log.exception("failed to build tools data")
        raise

    out_path.write_text(yaml_text, encoding="utf-8")
    tool_count = yaml_text.count("\n  - ")
    log.info("wrote tools data", path=str(out_path), tools=tool_count)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

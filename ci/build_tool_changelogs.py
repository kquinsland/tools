#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.14"
# dependencies = [
#   "structlog>=25.0.0",
#   "PyYAML>=6.0.0",
# ]
# ///
"""Update per-tool changelog.md files from git history.

Default behavior: update only existing changelog.md files.
Use --init to create changelog.md for tools that don't have one.
Use --tool (repeatable) to target specific tools by slug (e.g. html/3mf-inspector).
"""

from __future__ import annotations

import argparse
import logging
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

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


LOG = structlog.get_logger("ci.build_tool_changelogs")
HEADING_RE = re.compile(r"^##\s+`(?P<hash>[0-9a-f]{6,12})`", re.MULTILINE)
REPO_COMMITS_BASE = "https://github.com/kquinsland/tools/commits/main"
HISTORY_LINK_TEXT = "view history on github"


@dataclass(frozen=True)
class CommitInfo:
    short_hash: str
    date: str
    subject: str


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
    return structlog.get_logger("ci.build_tool_changelogs")


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


def _normalize_tool_slug(value: str) -> str:
    slug = value.strip().strip("/")
    if "content/tools/" in slug:
        slug = slug.split("content/tools/", 1)[1].strip("/")
    return slug


def _discover_tool_dirs(tools_root: Path) -> dict[str, Path]:
    tool_dirs: dict[str, Path] = {}
    for index in tools_root.rglob("index.md"):
        slug = index.parent.relative_to(tools_root).as_posix()
        if len(index.parent.relative_to(tools_root).parts) < 2:
            continue
        tool_dirs[slug] = index.parent
    for index in tools_root.rglob("_index.md"):
        slug = index.parent.relative_to(tools_root).as_posix()
        if len(index.parent.relative_to(tools_root).parts) < 2:
            continue
        tool_dirs[slug] = index.parent
    return tool_dirs


def _extract_top_hash(changelog_text: str) -> str | None:
    match = HEADING_RE.search(changelog_text)
    if not match:
        return None
    return match.group("hash")


def _parse_commit_lines(raw: str) -> list[CommitInfo]:
    commits: list[CommitInfo] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = line.split("\x1f")
        if len(parts) < 3:
            continue
        short_hash, date, subject = parts[0], parts[1], parts[2]
        subject = subject.strip() or "(no subject)"
        commits.append(CommitInfo(short_hash=short_hash, date=date, subject=subject))
    return commits


def _git_commits_for_tool(
    *,
    repo_root: Path,
    tool_dir: Path,
    tool_file: str,
    since_hash: str | None,
) -> list[CommitInfo]:
    rel_path = tool_dir.relative_to(repo_root) / tool_file
    args = [
        "log",
        "--format=%h%x1f%ad%x1f%s",
        "--date=format:%B %-d, %Y %H:%M",
    ]
    if since_hash:
        args.insert(1, f"{since_hash}..HEAD")
    args.extend(["--", str(rel_path)])
    raw = _run_git(args, cwd=repo_root)
    if not raw:
        return []
    return _parse_commit_lines(raw)


def _render_entries(commits: Iterable[CommitInfo]) -> str:
    blocks: list[str] = []
    for commit in commits:
        blocks.append(
            "\n".join(
                [
                    f"## `{commit.short_hash}` - {commit.date}",
                    "",
                    f"- {commit.subject}",
                ]
            )
        )
    return "\n\n".join(blocks)


def _read_tool_title(tool_dir: Path) -> str | None:
    candidates = [tool_dir / "_index.md", tool_dir / "index.md"]
    for path in candidates:
        if not path.exists():
            continue
        data = _read_front_matter(path)
        if not isinstance(data, dict):
            continue
        title = data.get("title")
        if isinstance(title, str) and title.strip():
            return title.strip()
    return None


def _read_front_matter(path: Path) -> dict[str, object] | None:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    end = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end = idx
            break
    if end is None:
        return None
    block = "\n".join(lines[1:end]).strip("\n")
    if not block.strip():
        return None
    try:
        data = yaml.safe_load(block)
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None


def _as_str_dict(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    return {str(key): item for key, item in value.items()}


def _read_tool_file(tool_dir: Path) -> str:
    candidates = [tool_dir / "_index.md", tool_dir / "index.md"]
    for path in candidates:
        if not path.exists():
            continue
        data = _read_front_matter(path)
        if not isinstance(data, dict):
            continue
        resources = data.get("resources")
        if isinstance(resources, list):
            for item in resources:
                item_dict = _as_str_dict(item)
                if not item_dict:
                    continue
                if item_dict.get("name") == "tool-file" and item_dict.get("src"):
                    return str(item_dict["src"])
        tool = _as_str_dict(data.get("tool"))
        toolbox = _as_str_dict(data.get("toolbox"))
        if tool and tool.get("file"):
            return str(tool["file"])
        if toolbox and toolbox.get("file"):
            return str(toolbox["file"])
    return "tool.html"


def _render_history_link(*, repo_root: Path, tool_dir: Path) -> str:
    tool_file = _read_tool_file(tool_dir)
    rel_path = tool_dir.relative_to(repo_root) / tool_file
    url = f"{REPO_COMMITS_BASE}/{rel_path.as_posix()}"
    return f"[{HISTORY_LINK_TEXT}]({url})"


def _render_front_matter(*, tool_dir: Path) -> str:
    tool_name = tool_dir.name
    if tool_name == "changelog":
        tool_name = tool_dir.parent.name
    title = _read_tool_title(tool_dir) or tool_name
    return "\n".join(
        [
            "---",
            f"title: Changelog - {title}",
            "bookHidden: true",
            "---",
            "",
        ]
    )


def _ensure_history_link(
    *,
    text: str,
    repo_root: Path,
    tool_dir: Path,
) -> str:
    link = _render_history_link(repo_root=repo_root, tool_dir=tool_dir)
    if not text.strip():
        return f"{link}\n"
    lines = [line for line in text.splitlines() if line.strip() != link]
    base = "\n".join(lines).rstrip()
    return f"{base}\n\n{link}\n"


def _update_changelog(
    *,
    repo_root: Path,
    tool_dir: Path,
    changelog_path: Path,
    init: bool,
) -> bool:
    if not changelog_path.exists() and not init:
        return False

    existing_text = ""
    if changelog_path.exists():
        existing_text = changelog_path.read_text(encoding="utf-8")

    if init:
        existing_text = ""
    else:
        existing_text = _ensure_history_link(
            text=existing_text,
            repo_root=repo_root,
            tool_dir=tool_dir,
        )

    top_hash = _extract_top_hash(existing_text)
    if top_hash is None and existing_text.strip():
        LOG.warning(
            "changelog missing heading hash; skipping",
            tool=str(tool_dir),
            path=str(changelog_path),
        )
        return False

    commits = _git_commits_for_tool(
        repo_root=repo_root,
        tool_dir=tool_dir,
        tool_file=_read_tool_file(tool_dir),
        since_hash=None if init and not top_hash else top_hash,
    )
    if not commits:
        return False

    new_block = _render_entries(commits)
    if existing_text.strip():
        updated = f"{new_block}\n\n{existing_text.lstrip()}"
    else:
        front_matter = _render_front_matter(tool_dir=tool_dir) if init else ""
        updated = f"{front_matter}{new_block}\n"
    updated = _ensure_history_link(
        text=updated,
        repo_root=repo_root,
        tool_dir=tool_dir,
    )
    changelog_path.write_text(updated, encoding="utf-8")
    return True


def _filter_tools(
    tool_dirs: dict[str, Path],
    selections: list[str],
) -> dict[str, Path]:
    if not selections:
        return tool_dirs
    normalized = {_normalize_tool_slug(item) for item in selections}
    selected: dict[str, Path] = {}
    for slug, path in tool_dirs.items():
        if slug in normalized:
            selected[slug] = path
    missing = sorted(normalized - set(selected))
    if missing:
        raise ValueError(f"Unknown tool(s): {', '.join(missing)}")
    return selected


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tool",
        action="append",
        default=[],
        help="Tool slug to update (e.g. html/3mf-inspector). Can be repeated.",
    )
    parser.add_argument(
        "--init",
        action="store_true",
        help="Create changelog.md for tools that do not have one.",
    )
    return parser.parse_args()


def main() -> int:
    _configure_logging()
    args = _parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    tools_root = repo_root / "content" / "tools"
    tool_dirs = _discover_tool_dirs(tools_root)
    selected = _filter_tools(tool_dirs, args.tool)

    updated = 0
    for slug, tool_dir in sorted(selected.items()):
        changelog_path = tool_dir / "changelog.md"
        if not args.init and not changelog_path.exists():
            continue
        if _update_changelog(
            repo_root=repo_root,
            tool_dir=tool_dir,
            changelog_path=changelog_path,
            init=args.init,
        ):
            updated += 1
            LOG.info("updated changelog", tool=slug, path=str(changelog_path))

    LOG.info("done", updated=updated)
    return 0


def test_extract_top_hash() -> None:
    content = "## `abc123` - January 1, 2025 10:00\n\n- Fix: Thing\n"
    assert _extract_top_hash(content) == "abc123"


def test_render_entries() -> None:
    commits = [
        CommitInfo(short_hash="abc123", date="January 1, 2025 10:00", subject="Fix A"),
        CommitInfo(short_hash="def456", date="January 2, 2025 11:00", subject="Add B"),
    ]
    rendered = _render_entries(commits)
    assert "## `abc123` - January 1, 2025 10:00" in rendered
    assert "- Fix A" in rendered
    assert "## `def456` - January 2, 2025 11:00" in rendered


def test_render_front_matter_uses_tool_title() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tool_dir = Path(tmp) / "html" / "yaml-json-convert-compare"
        tool_dir.mkdir(parents=True)
        (tool_dir / "_index.md").write_text(
            "\n".join(
                [
                    "---",
                    'title: "YAML ↔ JSON Convert & Compare"',
                    "---",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        front_matter = _render_front_matter(tool_dir=tool_dir)
        assert "title: Changelog - YAML ↔ JSON Convert & Compare" in front_matter


def test_render_history_link_uses_tool_file() -> None:
    repo_root = Path("/repo")
    tool_dir = repo_root / "content" / "tools" / "html" / "demo"
    tool_dir.mkdir(parents=True)
    (tool_dir / "_index.md").write_text(
        "\n".join(
            [
                "---",
                "resources:",
                "  - name: tool-file",
                "    src: custom.html",
                "---",
                "",
            ]
        ),
        encoding="utf-8",
    )
    link = _render_history_link(repo_root=repo_root, tool_dir=tool_dir)
    assert link.endswith("content/tools/html/demo/custom.html)")


def _git(args: list[str], *, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, text=True)


def test_update_changelog_from_last_hash() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        _git(["init"], cwd=repo)
        _git(["config", "user.email", "test@example.com"], cwd=repo)
        _git(["config", "user.name", "Test User"], cwd=repo)

        tool_dir = repo / "content" / "tools" / "html" / "demo"
        tool_dir.mkdir(parents=True)
        (tool_dir / "_index.md").write_text("---\n---\n", encoding="utf-8")
        (tool_dir / "tool.html").write_text("<html></html>", encoding="utf-8")
        _git(["add", "."], cwd=repo)
        _git(["commit", "-m", "Init tool"], cwd=repo)
        first_hash = _run_git(["rev-parse", "--short", "HEAD"], cwd=repo)

        changelog = tool_dir / "changelog.md"
        changelog.write_text(
            f"## `{first_hash}` - January 1, 2025 10:00\n\n- Init tool\n",
            encoding="utf-8",
        )

        (tool_dir / "tool.html").write_text("<html>v2</html>", encoding="utf-8")
        _git(["add", "."], cwd=repo)
        _git(["commit", "-m", "Fix: Update tool"], cwd=repo)
        second_hash = _run_git(["rev-parse", "--short", "HEAD"], cwd=repo)

        (tool_dir / "_index.md").write_text(
            "\n".join(
                [
                    "---",
                    "resources:",
                    "  - name: tool-file",
                    "    src: tool.html",
                    "---",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        _git(["add", "."], cwd=repo)
        _git(["commit", "-m", "Docs: Update index"], cwd=repo)

        changed = _update_changelog(
            repo_root=repo,
            tool_dir=tool_dir,
            changelog_path=changelog,
            init=False,
        )
        assert changed is True
        updated = changelog.read_text(encoding="utf-8")
        assert updated.startswith(f"## `{second_hash}`")
        assert f"## `{first_hash}`" in updated
        assert "Docs: Update index" not in updated


def test_init_creates_changelog() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        _git(["init"], cwd=repo)
        _git(["config", "user.email", "test@example.com"], cwd=repo)
        _git(["config", "user.name", "Test User"], cwd=repo)

        tool_dir = repo / "content" / "tools" / "html" / "demo"
        tool_dir.mkdir(parents=True)
        (tool_dir / "_index.md").write_text("---\n---\n", encoding="utf-8")
        (tool_dir / "tool.html").write_text("<html></html>", encoding="utf-8")
        _git(["add", "."], cwd=repo)
        _git(["commit", "-m", "Init tool"], cwd=repo)

        (tool_dir / "tool.html").write_text("<html>v2</html>", encoding="utf-8")
        _git(["add", "."], cwd=repo)
        _git(["commit", "-m", "Fix: Update tool"], cwd=repo)

        changelog = tool_dir / "changelog.md"
        changed = _update_changelog(
            repo_root=repo,
            tool_dir=tool_dir,
            changelog_path=changelog,
            init=True,
        )
        assert changed is True
        content = changelog.read_text(encoding="utf-8")
        assert "## `" in content
        assert "Fix: Update tool" in content


if __name__ == "__main__":
    raise SystemExit(main())

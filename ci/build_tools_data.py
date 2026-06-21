#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.14"
# dependencies = [
#   "structlog>=24.0.0",
#   "PyYAML>=6.0.0",
# ]
# ///
"""Build `data/tools.yaml` by walking `content/tools/**/_index.md`.

Rules (see PROBLEM.md):
- Each `content/tools/**/_index.md` is considered a tool entry unless:
  - it has `draft: true`, or
  - front matter contains `toolbox.ignore: true`
"""

from __future__ import annotations

import logging
import re
import subprocess
import tempfile
from collections import Counter
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse, urlunparse

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


def _get_tool_git_commits(
    tool_dir: Path, *, repo_root: Path | None = None
) -> tuple[str | None, str | None]:
    """Return (introduced_commit, updated_commit) for the tool directory.

    If there is no git history, returns (None, None).
    If the most recent commit matches the introduction commit, updated_commit is None.
    Generated per-tool changelogs and Hugo bundle landing pages are excluded to
    avoid self-referential updates from generated metadata or documentation-only
    tool page edits.
    """

    if repo_root is None:
        repo_root = Path(__file__).resolve().parents[1]
    rel_path = tool_dir.relative_to(repo_root)
    pathspecs = [
        str(rel_path),
        f":(exclude){(rel_path / '_index.md').as_posix()}",
        f":(exclude){(rel_path / 'index.md').as_posix()}",
        f":(exclude){(rel_path / 'changelog.md').as_posix()}",
    ]

    try:
        first_commit = _run_git(
            ["log", "--reverse", "--format=%H", "--", *pathspecs],
            cwd=repo_root,
        ).splitlines()
        if not first_commit:
            return None, None
        introduced_commit = first_commit[0].strip() or None

        latest_commit = (
            _run_git(
                ["log", "-n", "1", "--format=%H", "--", *pathspecs],
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
class Dependency:
    package: str
    version: str | None = None
    via: str | None = None


@dataclass(frozen=True)
class ToolEntry:
    slug: str
    title: str
    language: str
    description: str
    toolbox_file: str
    introduced_commit: str | None
    updated_commit: str | None
    dependencies: tuple[Dependency, ...]
    tags: tuple[str, ...]


def _iter_tool_index_files(tools_root: Path) -> Iterable[Path]:
    index_paths = list(tools_root.rglob("_index.md"))
    if not index_paths:
        index_paths = list(tools_root.rglob("index.md"))
    yield from sorted(index_paths)


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
    if len(rel_dir.parts) < 2:
        return None
    slug = rel_dir.as_posix()
    language = rel_dir.parts[0]

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

    tool_path = index_md.parent / toolbox_file
    dependencies = _extract_dependencies(language=language, tool_path=tool_path)
    introduced_commit, updated_commit = _get_tool_git_commits(index_md.parent)

    return ToolEntry(
        slug=slug,
        title=title,
        language=language,
        description=description,
        toolbox_file=toolbox_file,
        introduced_commit=introduced_commit,
        updated_commit=updated_commit,
        dependencies=dependencies,
        tags=tags,
    )


class _ScriptSrcParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.script_srcs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "script":
            return
        for attr, value in attrs:
            if attr.lower() == "src" and value:
                self.script_srcs.append(value)


def _url_without_query_fragment(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse(parsed._replace(query="", fragment=""))


def _parse_cdnjs_dependency(url: str) -> Dependency | None:
    parsed = urlparse(url)
    parts = parsed.path.strip("/").split("/")
    if len(parts) < 4 or parts[0] != "ajax" or parts[1] != "libs":
        return None
    package = parts[2]
    version = parts[3]
    if not package or not version:
        return None
    return Dependency(
        package=package,
        version=version,
        via=_url_without_query_fragment(url),
    )


def _parse_jsdelivr_dependency(url: str) -> Dependency | None:
    parsed = urlparse(url)
    parts = parsed.path.strip("/").split("/")
    if len(parts) < 2 or parts[0] != "npm":
        return None

    if parts[1].startswith("@"):
        if len(parts) < 3:
            return None
        scope = parts[1]
        package_part = parts[2]
        name, _, version = package_part.partition("@")
        if not name or not version:
            return None
        package = f"{scope}/{name}"
    else:
        name, _, version = parts[1].partition("@")
        if not name or not version:
            return None
        package = name

    return Dependency(
        package=package,
        version=version,
        via=_url_without_query_fragment(url),
    )


def _dependency_from_url(url: str) -> Dependency | None:
    if not url.startswith(("http://", "https://")):
        return None
    host = urlparse(url).netloc.lower()
    if host == "cdn.jsdelivr.net":
        return _parse_jsdelivr_dependency(url)
    if host == "cdnjs.cloudflare.com":
        return _parse_cdnjs_dependency(url)
    return None


def _parse_html_dependencies(html_text: str) -> list[Dependency]:
    parser = _ScriptSrcParser()
    parser.feed(html_text)
    dependencies: list[Dependency] = []
    seen: set[tuple[str, str | None, str | None]] = set()
    for src in parser.script_srcs:
        dependency = _dependency_from_url(src)
        if dependency is None:
            continue
        key = (dependency.package, dependency.version, dependency.via)
        if key in seen:
            continue
        seen.add(key)
        dependencies.append(dependency)
    return dependencies


def _extract_pep723_block(script_text: str) -> list[str]:
    lines = script_text.splitlines()
    in_block = False
    block_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped == "# /// script":
            in_block = True
            continue
        if in_block and stripped == "# ///":
            break
        if not in_block:
            continue
        if not line.lstrip().startswith("#"):
            continue
        content = line.lstrip()[1:]
        if content.startswith(" "):
            content = content[1:]
        block_lines.append(content.rstrip())
    return block_lines


def _parse_pep723_dependencies(script_text: str) -> list[str]:
    block_lines = _extract_pep723_block(script_text)
    if not block_lines:
        return []

    deps: list[str] = []
    in_list = False
    for line in block_lines:
        stripped = line.strip()
        if not in_list:
            if not stripped.startswith("dependencies"):
                continue
            _, _, rest = stripped.partition("=")
            rest = rest.strip()
            if not rest.startswith("["):
                continue
            in_list = True
            rest = rest[1:]
        else:
            rest = stripped

        if "]" in rest:
            before, _, _ = rest.partition("]")
            deps.extend(re.findall(r"['\"]([^'\"]+)['\"]", before))
            break
        deps.extend(re.findall(r"['\"]([^'\"]+)['\"]", rest))
    return deps


_REQ_RE = re.compile(r"^\s*([A-Za-z0-9_.-]+)(\[[^\]]+\])?\s*(.*)$")


def _parse_requirement(requirement: str) -> Dependency:
    match = _REQ_RE.match(requirement)
    if not match:
        return Dependency(package=requirement.strip() or requirement)
    name, extras, spec = match.groups()
    package = f"{name}{extras or ''}"
    version = spec.strip() or None
    return Dependency(package=package, version=version)


def _parse_python_dependencies(script_text: str) -> list[Dependency]:
    requirements = _parse_pep723_dependencies(script_text)
    return [_parse_requirement(requirement) for requirement in requirements]


def _extract_dependencies(*, language: str, tool_path: Path) -> tuple[Dependency, ...]:
    if not tool_path.exists():
        return ()
    try:
        tool_text = tool_path.read_text(encoding="utf-8")
    except OSError:
        return ()
    if language == "html":
        return tuple(_parse_html_dependencies(tool_text))
    if language == "python":
        return tuple(_parse_python_dependencies(tool_text))
    return ()


def _dependency_host(dependency: Dependency) -> str | None:
    if dependency.via is None:
        return None
    parsed = urlparse(dependency.via)
    return parsed.netloc.lower() or None


def _build_tools_stats(entries: list[ToolEntry]) -> dict[str, Any]:
    language_counts: Counter[str] = Counter()
    host_counts: Counter[str] = Counter()
    dependency_counts: dict[str, Counter[tuple[str, str | None]]] = {}
    dependency_tools: dict[str, list[ToolEntry]] = {}

    tools_with_dependencies = 0
    for entry in entries:
        language_counts[entry.language] += 1

        if not entry.dependencies:
            continue

        tools_with_dependencies += 1
        dependency_tools.setdefault(entry.language, []).append(entry)

        seen_for_tool: set[tuple[str, str | None]] = set()
        for dependency in entry.dependencies:
            if host := _dependency_host(dependency):
                host_counts[host] += 1

            dep_key = (dependency.package, dependency.version)
            if dep_key in seen_for_tool:
                continue
            seen_for_tool.add(dep_key)
            counts_for_language = dependency_counts.setdefault(
                entry.language, Counter()
            )
            counts_for_language[dep_key] += 1

    dependencies_by_language = []
    for language in sorted(dependency_counts):
        dependency_items = []
        for (package, version), count in sorted(
            dependency_counts[language].items(),
            key=lambda item: (-item[1], item[0][0], item[0][1] or ""),
        ):
            dependency_items.append(
                {
                    "package": package,
                    "version": version,
                    "count": count,
                }
            )
        dependencies_by_language.append(
            {
                "language": language,
                "dependencies": dependency_items,
            }
        )

    dependency_tools_by_language = []
    for language in sorted(dependency_tools):
        tools = []
        for entry in sorted(
            dependency_tools[language],
            key=lambda tool: (tool.title.lower(), tool.slug),
        ):
            tools.append(
                {
                    "slug": entry.slug,
                    "title": entry.title,
                    "dependencies": entry.dependencies,
                }
            )
        dependency_tools_by_language.append({"language": language, "tools": tools})

    return {
        "total_tools": len(entries),
        "tools_with_dependencies": tools_with_dependencies,
        "tools_without_dependencies": len(entries) - tools_with_dependencies,
        "languages": [
            {"language": language, "count": count}
            for language, count in sorted(language_counts.items())
        ],
        "dependency_hosts": [
            {"host": host, "count": count}
            for host, count in sorted(
                host_counts.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ],
        "dependencies_by_language": dependencies_by_language,
        "dependency_tools_by_language": dependency_tools_by_language,
    }


def _append_dependency_yaml(
    lines: list[str], dependency: Dependency, indent: str
) -> None:
    lines.append(f"{indent}- package: {_yaml_quote(dependency.package)}")
    if dependency.version is not None:
        lines.append(f"{indent}  version: {_yaml_quote(dependency.version)}")
    if dependency.via is not None:
        lines.append(f"{indent}  via: {_yaml_quote(dependency.via)}")


def _append_stats_yaml(lines: list[str], stats: dict[str, Any]) -> None:
    lines.append("stats:")
    lines.append(f"  total_tools: {stats['total_tools']}")
    lines.append(f"  tools_with_dependencies: {stats['tools_with_dependencies']}")
    lines.append(f"  tools_without_dependencies: {stats['tools_without_dependencies']}")

    lines.append("  languages:")
    for language in stats["languages"]:
        lines.append(f"    - language: {_yaml_quote(language['language'])}")
        lines.append(f"      count: {language['count']}")
    if not stats["languages"]:
        lines[-1] = "  languages: []"

    lines.append("  dependency_hosts:")
    for host in stats["dependency_hosts"]:
        lines.append(f"    - host: {_yaml_quote(host['host'])}")
        lines.append(f"      count: {host['count']}")
    if not stats["dependency_hosts"]:
        lines[-1] = "  dependency_hosts: []"

    lines.append("  dependencies_by_language:")
    for language_group in stats["dependencies_by_language"]:
        lines.append(f"    - language: {_yaml_quote(language_group['language'])}")
        dependencies = language_group["dependencies"]
        if not dependencies:
            lines.append("      dependencies: []")
            continue
        lines.append("      dependencies:")
        for dependency in dependencies:
            lines.append(f"        - package: {_yaml_quote(dependency['package'])}")
            if dependency["version"] is not None:
                lines.append(f"          version: {_yaml_quote(dependency['version'])}")
            lines.append(f"          count: {dependency['count']}")
    if not stats["dependencies_by_language"]:
        lines[-1] = "  dependencies_by_language: []"

    lines.append("  dependency_tools_by_language:")
    for language_group in stats["dependency_tools_by_language"]:
        lines.append(f"    - language: {_yaml_quote(language_group['language'])}")
        tools = language_group["tools"]
        if not tools:
            lines.append("      tools: []")
            continue
        lines.append("      tools:")
        for tool in tools:
            lines.append(f"        - slug: {_yaml_quote(tool['slug'])}")
            lines.append(f"          title: {_yaml_quote(tool['title'])}")
            dependencies = tool["dependencies"]
            if not dependencies:
                lines.append("          dependencies: []")
                continue
            lines.append("          dependencies:")
            for dependency in dependencies:
                _append_dependency_yaml(lines, dependency, "            ")
    if not stats["dependency_tools_by_language"]:
        lines[-1] = "  dependency_tools_by_language: []"


def _render_tools_yaml(entries: list[ToolEntry]) -> str:
    lines: list[str] = ["---", "version: 2"]
    _append_stats_yaml(lines, _build_tools_stats(entries))

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
        if entry.dependencies:
            lines.append("      dependencies:")
            for dependency in entry.dependencies:
                _append_dependency_yaml(lines, dependency, "        ")
        if entry.tags:
            lines.append("      tags:")
            for tag in entry.tags:
                lines.append(f"        - {_yaml_quote(tag)}")

    return "\n".join(lines) + "\n"


def _load_base_url(*, repo_root: Path) -> str:
    config_path = repo_root / "hugo.yaml"
    if not config_path.exists():
        return ""
    try:
        config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return ""
    base_url = str(config.get("baseURL") or "").strip()
    if base_url:
        return base_url.rstrip("/") + "/"
    return ""


def _format_language_heading(language: str) -> str:
    normalized = language.strip().lower()
    if normalized == "html":
        return "HTML"
    if normalized == "python":
        return "Python"
    if not normalized:
        return "Other"
    return normalized.title()


def _render_tools_txt(*, entries: list[ToolEntry], base_url: str) -> str:
    if not entries:
        return "# Tools\n\n_No tools available._\n"

    tools_by_language: dict[str, list[ToolEntry]] = {}
    for entry in entries:
        tools_by_language.setdefault(entry.language, []).append(entry)

    lines: list[str] = ["# Tools", ""]
    for language in sorted(tools_by_language):
        heading = _format_language_heading(language)
        lines.append(f"## Tools ({heading})")
        lines.append("")
        for entry in sorted(tools_by_language[language], key=lambda e: e.title.lower()):
            if base_url:
                url = f"{base_url}tools/{entry.slug}/"
            else:
                url = f"/tools/{entry.slug}/"
            if entry.description:
                lines.append(f"- [{entry.title}]({url}): {entry.description}")
            else:
                lines.append(f"- [{entry.title}]({url})")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def build_tools_yaml(*, repo_root: Path) -> str:
    tools_root = repo_root / "content" / "tools"
    entries: list[ToolEntry] = []
    for index_md in _iter_tool_index_files(tools_root):
        entry = _build_tool_entry(index_md, tools_root=tools_root)
        if entry is not None:
            entries.append(entry)

    entries.sort(key=lambda e: e.slug)
    return _render_tools_yaml(entries)


def build_tools_txt(*, repo_root: Path) -> str:
    tools_root = repo_root / "content" / "tools"
    entries: list[ToolEntry] = []
    for index_md in _iter_tool_index_files(tools_root):
        entry = _build_tool_entry(index_md, tools_root=tools_root)
        if entry is not None:
            entries.append(entry)

    entries.sort(key=lambda e: (e.language.lower(), e.title.lower()))
    base_url = _load_base_url(repo_root=repo_root)
    return _render_tools_txt(entries=entries, base_url=base_url)


def test_parse_jsdelivr_dependency() -> None:
    url = "https://cdn.jsdelivr.net/npm/jszip@3.10.1/dist/jszip.min.js"
    dependency = _parse_jsdelivr_dependency(url)
    assert dependency == Dependency(
        package="jszip",
        version="3.10.1",
        via="https://cdn.jsdelivr.net/npm/jszip@3.10.1/dist/jszip.min.js",
    )


def test_parse_cdnjs_dependency() -> None:
    url = "https://cdnjs.cloudflare.com/ajax/libs/viz.js/2.1.2/viz.js"
    dependency = _parse_cdnjs_dependency(url)
    assert dependency == Dependency(
        package="viz.js",
        version="2.1.2",
        via="https://cdnjs.cloudflare.com/ajax/libs/viz.js/2.1.2/viz.js",
    )


def test_parse_html_dependencies_dedupes() -> None:
    html_text = """
    <html>
      <head>
        <script src="https://cdn.jsdelivr.net/npm/jszip@3.10.1/dist/jszip.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/jszip@3.10.1/dist/jszip.min.js"></script>
      </head>
    </html>
    """
    dependencies = _parse_html_dependencies(html_text)
    assert dependencies == [
        Dependency(
            package="jszip",
            version="3.10.1",
            via="https://cdn.jsdelivr.net/npm/jszip@3.10.1/dist/jszip.min.js",
        )
    ]


def test_parse_pep723_dependencies() -> None:
    marker = "# " + "///"
    script_text = "\n".join(
        [
            "#!/usr/bin/env -S uv run",
            f"{marker} script",
            '# requires-python = ">=3.11"',
            "# dependencies = [",
            '#   "click>=8.1",',
            '#   "structlog>=24.0",',
            '#   "pyyaml>=6.0",',
            "# ]",
            marker,
            "",
        ]
    )
    dependencies = _parse_python_dependencies(script_text)
    assert dependencies == [
        Dependency(package="click", version=">=8.1"),
        Dependency(package="structlog", version=">=24.0"),
        Dependency(package="pyyaml", version=">=6.0"),
    ]


def test_parse_requirement_with_extras() -> None:
    dependency = _parse_requirement("requests[socks]>=2.31")
    assert dependency == Dependency(package="requests[socks]", version=">=2.31")


def _stats_test_entry(
    *,
    slug: str,
    title: str,
    language: str,
    dependencies: tuple[Dependency, ...] = (),
) -> ToolEntry:
    return ToolEntry(
        slug=slug,
        title=title,
        language=language,
        description="",
        toolbox_file="tool.html",
        introduced_commit=None,
        updated_commit=None,
        dependencies=dependencies,
        tags=(),
    )


def test_build_tools_stats_counts_tools_and_languages() -> None:
    entries = [
        _stats_test_entry(
            slug="python/beta",
            title="Beta",
            language="python",
            dependencies=(Dependency(package="click", version=">=8.1"),),
        ),
        _stats_test_entry(slug="html/alpha", title="Alpha", language="html"),
        _stats_test_entry(slug="html/gamma", title="Gamma", language="html"),
    ]

    stats = _build_tools_stats(entries)

    assert stats["total_tools"] == 3
    assert stats["tools_with_dependencies"] == 1
    assert stats["tools_without_dependencies"] == 2
    assert stats["languages"] == [
        {"language": "html", "count": 2},
        {"language": "python", "count": 1},
    ]


def test_build_tools_stats_dedupes_dependency_counts_per_tool() -> None:
    entries = [
        _stats_test_entry(
            slug="html/alpha",
            title="Alpha",
            language="html",
            dependencies=(
                Dependency(package="jszip", version="3.10.1"),
                Dependency(package="jszip", version="3.10.1"),
                Dependency(package="exifr", version="7.1.3"),
            ),
        ),
        _stats_test_entry(
            slug="html/beta",
            title="Beta",
            language="html",
            dependencies=(Dependency(package="jszip", version="3.10.1"),),
        ),
    ]

    stats = _build_tools_stats(entries)

    assert stats["dependencies_by_language"] == [
        {
            "language": "html",
            "dependencies": [
                {"package": "jszip", "version": "3.10.1", "count": 2},
                {"package": "exifr", "version": "7.1.3", "count": 1},
            ],
        }
    ]


def test_build_tools_stats_counts_dependency_hosts_from_via() -> None:
    entries = [
        _stats_test_entry(
            slug="html/alpha",
            title="Alpha",
            language="html",
            dependencies=(
                Dependency(
                    package="one",
                    version="1.0.0",
                    via="https://cdn.jsdelivr.net/npm/one@1.0.0/index.js",
                ),
                Dependency(
                    package="two",
                    version="1.0.0",
                    via="https://cdnjs.cloudflare.com/ajax/libs/two/1.0.0/two.js",
                ),
                Dependency(
                    package="three",
                    version="1.0.0",
                    via="https://cdn.jsdelivr.net/npm/three@1.0.0/index.js",
                ),
            ),
        )
    ]

    stats = _build_tools_stats(entries)

    assert stats["dependency_hosts"] == [
        {"host": "cdn.jsdelivr.net", "count": 2},
        {"host": "cdnjs.cloudflare.com", "count": 1},
    ]


def test_build_tools_stats_sorts_dependencies_and_tools_deterministically() -> None:
    entries = [
        _stats_test_entry(
            slug="html/zulu",
            title="Zulu",
            language="html",
            dependencies=(
                Dependency(package="beta", version="1.0.0"),
                Dependency(package="alpha", version="2.0.0"),
                Dependency(package="alpha", version="1.0.0"),
            ),
        ),
        _stats_test_entry(
            slug="html/alpha",
            title="Alpha",
            language="html",
            dependencies=(
                Dependency(package="beta", version="1.0.0"),
                Dependency(package="alpha", version="1.0.0"),
            ),
        ),
        _stats_test_entry(
            slug="python/bravo",
            title="Bravo",
            language="python",
            dependencies=(Dependency(package="click", version=">=8.1"),),
        ),
    ]

    stats = _build_tools_stats(entries)

    assert stats["dependencies_by_language"] == [
        {
            "language": "html",
            "dependencies": [
                {"package": "alpha", "version": "1.0.0", "count": 2},
                {"package": "beta", "version": "1.0.0", "count": 2},
                {"package": "alpha", "version": "2.0.0", "count": 1},
            ],
        },
        {
            "language": "python",
            "dependencies": [
                {"package": "click", "version": ">=8.1", "count": 1},
            ],
        },
    ]
    assert [
        (group["language"], [tool["slug"] for tool in group["tools"]])
        for group in stats["dependency_tools_by_language"]
    ] == [
        ("html", ["html/alpha", "html/zulu"]),
        ("python", ["python/bravo"]),
    ]


def _git(args: list[str], *, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, text=True)


def test_tool_git_commits_ignore_generated_changelog() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        _git(["init"], cwd=repo)
        _git(["config", "user.email", "test@example.com"], cwd=repo)
        _git(["config", "user.name", "Test User"], cwd=repo)

        tool_dir = repo / "content" / "tools" / "html" / "demo"
        tool_dir.mkdir(parents=True)
        (tool_dir / "_index.md").write_text("---\ntitle: Demo\n---\n", encoding="utf-8")
        (tool_dir / "tool.html").write_text("<html>v1</html>", encoding="utf-8")
        _git(["add", "."], cwd=repo)
        _git(["commit", "-m", "Add demo tool"], cwd=repo)
        introduced = _run_git(["rev-parse", "HEAD"], cwd=repo)

        (tool_dir / "changelog.md").write_text("## generated\n", encoding="utf-8")
        _git(["add", "."], cwd=repo)
        _git(["commit", "-m", "Refresh changelog"], cwd=repo)

        assert _get_tool_git_commits(tool_dir, repo_root=repo) == (introduced, None)

        (tool_dir / "_index.md").write_text(
            "---\ntitle: Demo\n---\n\nUpdated page copy.\n",
            encoding="utf-8",
        )
        _git(["add", "."], cwd=repo)
        _git(["commit", "-m", "Update tool page copy"], cwd=repo)

        assert _get_tool_git_commits(tool_dir, repo_root=repo) == (introduced, None)

        (tool_dir / "tool.html").write_text("<html>v2</html>", encoding="utf-8")
        _git(["add", "."], cwd=repo)
        _git(["commit", "-m", "Update demo tool"], cwd=repo)
        updated = _run_git(["rev-parse", "HEAD"], cwd=repo)

        (tool_dir / "changelog.md").write_text("## generated again\n", encoding="utf-8")
        _git(["add", "."], cwd=repo)
        _git(["commit", "-m", "Refresh changelog again"], cwd=repo)

        assert _get_tool_git_commits(tool_dir, repo_root=repo) == (introduced, updated)


def main() -> int:
    log = _configure_logging()
    repo_root = Path(__file__).resolve().parents[1]
    tools_root = repo_root / "content" / "tools"
    out_path = repo_root / "data" / "tools.yaml"
    static_yaml_path = repo_root / "static" / "tools.yaml"
    tools_txt_path = repo_root / "static" / "tools.txt"

    log.info("building tools data", tools_root=tools_root)
    try:
        yaml_text = build_tools_yaml(repo_root=repo_root)
        tools_txt = build_tools_txt(repo_root=repo_root)
    except Exception:
        log.exception("failed to build tools data")
        raise

    out_path.write_text(yaml_text, encoding="utf-8")
    static_yaml_path.write_text(yaml_text, encoding="utf-8")
    tools_txt_path.write_text(tools_txt, encoding="utf-8")
    parsed_tools_data = yaml.safe_load(yaml_text) or {}
    tool_count = parsed_tools_data.get("stats", {}).get("total_tools", 0)
    log.info("wrote tools data", path=str(out_path), tools=tool_count)
    log.info("wrote public tools data", path=str(static_yaml_path))
    log.info("wrote tools listing", path=str(tools_txt_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

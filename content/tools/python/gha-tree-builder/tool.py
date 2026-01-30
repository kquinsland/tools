#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.14"
# dependencies = [
#   "click>=8.1",
#   "structlog>=24.0",
#   "pyyaml>=6.0",
#   "pydot>=2.0",
# ]
# ///
"""Generate a DOT graph of GitHub Actions workflow triggers and dependencies."""

from __future__ import annotations

import glob
import logging
from dataclasses import dataclass
import hashlib
import re
from pathlib import Path
from typing import Any, Iterable, Mapping

import click
import pydot
import structlog
import yaml


@dataclass(frozen=True)
class WorkflowInfo:
    name: str
    path: Path
    raw: dict[object, Any]


@dataclass(frozen=True)
class GraphEdge:
    source: str
    target: str
    label: str | None = None


def configure_logging(verbose: bool) -> structlog.stdlib.BoundLogger:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO, format="%(message)s"
    )
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
            structlog.processors.add_log_level,
            structlog.dev.ConsoleRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    return structlog.get_logger()


def resolve_globs(root: Path, globs: Iterable[str]) -> set[Path]:
    matches: set[Path] = set()
    for pattern in globs:
        pattern_path = Path(pattern)
        if pattern_path.is_absolute():
            for match in glob.glob(pattern):
                matches.add(Path(match))
        else:
            matches.update(root.glob(pattern))
    return matches


def list_workflow_files(
    root: Path,
    patterns: Iterable[str] | None = None,
    include_globs: Iterable[str] | None = None,
    exclude_globs: Iterable[str] | None = None,
) -> list[Path]:
    if not root.exists():
        raise FileNotFoundError(f"Workflow root not found: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Workflow root is not a directory: {root}")

    candidates: list[Path]
    if patterns:
        candidates = sorted(resolve_globs(root, patterns))
    else:
        candidates = sorted(root.iterdir())

    if include_globs:
        include_matches = resolve_globs(root, include_globs)
        candidates = [path for path in candidates if path in include_matches]
    if exclude_globs:
        exclude_matches = resolve_globs(root, exclude_globs)
        candidates = [path for path in candidates if path not in exclude_matches]

    return [
        path
        for path in candidates
        if path.is_file() and path.suffix in {".yml", ".yaml"}
    ]


def load_yaml(path: Path, logger: structlog.stdlib.BoundLogger) -> dict[object, Any]:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("failed_to_read", path=str(path), error=str(exc))
        return {}

    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        logger.warning("failed_to_parse_yaml", path=str(path), error=str(exc))
        return {}

    if not isinstance(data, dict):
        logger.warning(
            "unexpected_yaml_root", path=str(path), value_type=type(data).__name__
        )
        return {}
    return data


def workflow_name(path: Path, raw: Mapping[object, Any]) -> str:
    name = raw.get("name")
    if isinstance(name, str) and name.strip():
        return name.strip()
    return path.stem


def get_on_section(raw: Mapping[object, Any]) -> Any:
    if "on" in raw:
        return raw.get("on")
    # PyYAML treats unquoted "on" as boolean True in YAML 1.1
    if True in raw:
        return raw.get(True)
    return None


def normalize_event_label(event: str, details: str | None = None) -> str:
    if details:
        return f"{event}: {details}"
    return event


def parse_trigger_details(event: str, value: Any) -> list[str]:
    if event == "schedule" and isinstance(value, list):
        labels = []
        for entry in value:
            if isinstance(entry, dict) and "cron" in entry:
                labels.append(
                    normalize_event_label("schedule", str(entry["cron"]).strip())
                )
        return labels

    if isinstance(value, dict):
        types = value.get("types")
        if isinstance(types, str):
            return [normalize_event_label(event, types)]
        if isinstance(types, list):
            return [normalize_event_label(event, str(item)) for item in types]

    return [event]


def extract_triggers(raw: Mapping[object, Any]) -> list[str]:
    on_section = get_on_section(raw)
    if on_section is None:
        return []

    if isinstance(on_section, str):
        return [on_section]

    if isinstance(on_section, list):
        return [str(item) for item in on_section]

    if isinstance(on_section, dict):
        labels: list[str] = []
        for event, value in sorted(on_section.items(), key=lambda item: str(item[0])):
            labels.extend(parse_trigger_details(str(event), value))
        return labels

    return []


def extract_workflow_run_sources(raw: Mapping[object, Any]) -> list[str]:
    on_section = get_on_section(raw)
    if not isinstance(on_section, dict):
        return []
    workflow_run = on_section.get("workflow_run")
    if not isinstance(workflow_run, dict):
        return []
    workflows = workflow_run.get("workflows")
    if isinstance(workflows, str):
        return [workflows]
    if isinstance(workflows, list):
        return [str(item) for item in workflows]
    return []


def extract_jobs(raw: Mapping[object, Any]) -> dict[str, dict[str, Any]]:
    jobs = raw.get("jobs")
    if isinstance(jobs, dict):
        return jobs
    return {}


def is_workflow_file(raw: Mapping[object, Any]) -> bool:
    has_on = get_on_section(raw) is not None
    has_jobs = bool(extract_jobs(raw))
    return has_on and has_jobs


def parse_uses_target(uses: str, workflow_map: dict[str, str]) -> tuple[str, bool]:
    if "/.github/workflows/" in uses:
        fragment = uses.split("/.github/workflows/", maxsplit=1)[-1]
        file_part = fragment.split("@", maxsplit=1)[0]
        file_name = Path(file_part).name
        if file_name in workflow_map:
            return workflow_map[file_name], True
    return uses, False


def build_graph(
    workflows: Iterable[WorkflowInfo],
    workflow_map: dict[str, str],
) -> pydot.Dot:
    graph = pydot.Dot(graph_type="digraph", rankdir="LR")

    node_registry: dict[str, pydot.Node] = {}
    edges: list[GraphEdge] = []

    def stable_node_id(kind: str, name: str) -> str:
        slug = re.sub(r"[^A-Za-z0-9_]", "_", name).strip("_") or "node"
        digest = hashlib.sha1(f"{kind}:{name}".encode("utf-8")).hexdigest()[:8]
        return f"{kind}_{slug}_{digest}"

    def add_node(node_id: str, label: str, **attrs: str) -> None:
        if node_id in node_registry:
            return
        node = pydot.Node(node_id, label=label, **attrs)
        node_registry[node_id] = node
        graph.add_node(node)

    def add_edge(source: str, target: str, label: str | None = None) -> None:
        edges.append(GraphEdge(source=source, target=target, label=label))

    for workflow in workflows:
        workflow_node = stable_node_id("workflow", workflow.name)
        add_node(
            workflow_node,
            workflow.name,
            shape="box",
            style="rounded,filled",
            fillcolor="#e8eef7",
            color="#4a5d7a",
        )

        triggers = extract_triggers(workflow.raw)
        for trigger in triggers:
            trigger_node = stable_node_id("trigger", f"{workflow.name}::{trigger}")
            add_node(
                trigger_node,
                trigger,
                shape="diamond",
                style="filled",
                fillcolor="#f7efe0",
                color="#8a6b3f",
            )
            add_edge(trigger_node, workflow_node)

        for source_name in extract_workflow_run_sources(workflow.raw):
            source_node = stable_node_id("workflow", source_name)
            add_node(
                source_node,
                source_name,
                shape="box",
                style="rounded,filled",
                fillcolor="#f0f0f0",
                color="#7a7a7a",
            )
            add_edge(source_node, workflow_node, label="workflow_run")

        jobs = extract_jobs(workflow.raw)
        for job_id, job_data in sorted(jobs.items(), key=lambda item: item[0]):
            job_node = stable_node_id("job", f"{workflow.name}::{job_id}")
            add_node(
                job_node,
                job_id,
                shape="ellipse",
                style="filled",
                fillcolor="#e9f6ef",
                color="#3d7a57",
            )
            add_edge(workflow_node, job_node)

            if isinstance(job_data, dict):
                needs = job_data.get("needs")
                if isinstance(needs, str):
                    add_edge(
                        stable_node_id("job", f"{workflow.name}::{needs}"),
                        job_node,
                        label="needs",
                    )
                elif isinstance(needs, list):
                    for dep in needs:
                        add_edge(
                            stable_node_id("job", f"{workflow.name}::{dep}"),
                            job_node,
                            label="needs",
                        )

                uses = job_data.get("uses")
                if isinstance(uses, str):
                    target_name, is_local = parse_uses_target(uses, workflow_map)
                    target_node = stable_node_id("workflow", target_name)
                    add_node(
                        target_node,
                        target_name,
                        shape="box",
                        style="rounded,filled" if is_local else "dashed,rounded",
                        fillcolor="#e8eef7" if is_local else "#ffffff",
                        color="#4a5d7a" if is_local else "#7a7a7a",
                    )
                    add_edge(job_node, target_node, label="calls")

    for edge in edges:
        graph.add_edge(pydot.Edge(edge.source, edge.target, label=edge.label or ""))

    return graph


def build_workflow_map(workflows: Iterable[WorkflowInfo]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for workflow in workflows:
        mapping[workflow.path.name] = workflow.name
    return mapping


def collect_workflows(
    root: Path,
    logger: structlog.stdlib.BoundLogger,
    patterns: Iterable[str] | None = None,
    include_globs: Iterable[str] | None = None,
    exclude_globs: Iterable[str] | None = None,
) -> list[WorkflowInfo]:
    workflows = []
    for path in list_workflow_files(
        root,
        patterns=patterns,
        include_globs=include_globs,
        exclude_globs=exclude_globs,
    ):
        raw = load_yaml(path, logger)
        if not raw:
            continue
        if not is_workflow_file(raw):
            logger.warning("skipping_non_workflow_file", path=str(path))
            continue
        workflows.append(
            WorkflowInfo(name=workflow_name(path, raw), path=path, raw=raw)
        )
    return workflows


def write_dot(graph: pydot.Dot, output: Path) -> None:
    output.write_text(graph.to_string(), encoding="utf-8")


def render_graph(graph: pydot.Dot, output: Path) -> None:
    suffix = output.suffix.lower().lstrip(".")
    if not suffix:
        raise click.ClickException(
            "Render output must include a file extension to infer the format."
        )

    format_map = {"jpg": "jpeg"}
    fmt = format_map.get(suffix, suffix)
    supported = {"png", "svg", "pdf", "webp", "jpeg"}
    if fmt not in supported:
        raise click.ClickException(f"Unsupported render format: .{suffix}")

    if fmt == "png":
        graph.write_png(str(output))
        return
    graph.write(str(output), format=fmt)


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--workflow-root",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=None,
    envvar="GHA_TREE_BUILDER_WORKFLOW_ROOT",
    help="Directory containing workflow YAML files (default: current directory).",
)
@click.option(
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    envvar="GHA_TREE_BUILDER_OUTPUT",
    help="Output DOT file path (default: ./gha-tree.dot).",
)
@click.option(
    "--render",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    envvar="GHA_TREE_BUILDER_RENDER",
    help=(
        "Render graph output (format inferred from extension; requires Graphviz in PATH)."
    ),
)
@click.option(
    "--no-dot",
    is_flag=True,
    envvar="GHA_TREE_BUILDER_NO_DOT",
    help="Skip writing the DOT output file.",
)
@click.option(
    "--include-glob",
    "include_globs",
    multiple=True,
    envvar="GHA_TREE_BUILDER_INCLUDE_GLOB",
    help=(
        "Only include workflow files matching glob(s). Mutually exclusive with "
        "--exclude-glob and positional patterns."
    ),
)
@click.option(
    "--exclude-glob",
    "exclude_globs",
    multiple=True,
    envvar="GHA_TREE_BUILDER_EXCLUDE_GLOB",
    help=(
        "Exclude workflow files matching glob(s). Mutually exclusive with "
        "--include-glob and positional patterns."
    ),
)
@click.argument("patterns", nargs=-1)
@click.option(
    "--verbose",
    is_flag=True,
    envvar="GHA_TREE_BUILDER_VERBOSE",
    help="Enable verbose logging.",
)
def main(
    workflow_root: Path | None,
    output: Path | None,
    render: Path | None,
    no_dot: bool,
    include_globs: tuple[str, ...],
    exclude_globs: tuple[str, ...],
    patterns: tuple[str, ...],
    verbose: bool,
) -> None:
    """Generate a DOT file describing GitHub Actions workflow dependencies."""
    logger = configure_logging(verbose)

    root = workflow_root or Path.cwd()
    output_path = output or (Path.cwd() / "gha-tree.dot")

    if include_globs and exclude_globs:
        raise click.ClickException(
            "--include-glob and --exclude-glob cannot be used together."
        )
    if patterns and (include_globs or exclude_globs):
        raise click.ClickException(
            "Positional patterns cannot be combined with --include-glob or --exclude-glob."
        )

    log_payload: dict[str, Any] = {"workflow_root": str(root)}
    if not no_dot:
        log_payload["output"] = str(output_path)
    if patterns:
        log_payload["patterns"] = list(patterns)
    if include_globs:
        log_payload["include_glob"] = list(include_globs)
    if exclude_globs:
        log_payload["exclude_glob"] = list(exclude_globs)
    logger.info("building_graph", **log_payload)

    workflows = collect_workflows(
        root,
        logger,
        patterns=patterns or None,
        include_globs=include_globs or None,
        exclude_globs=exclude_globs or None,
    )
    if not workflows:
        logger.warning("no_workflows_found", workflow_root=str(root))

    workflow_map = build_workflow_map(workflows)
    graph = build_graph(workflows, workflow_map)

    if not no_dot:
        try:
            write_dot(graph, output_path)
            logger.info("dot_written", output=str(output_path))
        except OSError as exc:
            raise click.ClickException(f"Failed to write DOT file: {exc}") from exc
    else:
        logger.info("dot_skipped", reason="--no-dot")

    if render:
        try:
            logger.info("rendering_graph", output=str(render))
            render_graph(graph, render)
            logger.info("render_written", output=str(render))
        except (
            Exception
        ) as exc:  # pydot raises generic exceptions when Graphviz is missing
            logger.warning("render_failed", output=str(render), error=str(exc))


def test_extract_triggers_schedule() -> None:
    raw = {"on": {"schedule": [{"cron": "0 0 * * *"}]}}
    assert extract_triggers(raw) == ["schedule: 0 0 * * *"]


def test_build_graph_with_job_calls(tmp_path: Path) -> None:
    workflow_a = tmp_path / "a.yml"
    workflow_b = tmp_path / "b.yml"

    workflow_a.write_text(
        """
name: Workflow A
on: [push]
jobs:
  call_b:
    uses: ./.github/workflows/b.yml
""".strip(),
        encoding="utf-8",
    )

    workflow_b.write_text(
        """
name: Workflow B
on: workflow_call
jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - run: echo hi
""".strip(),
        encoding="utf-8",
    )

    logger = configure_logging(False)
    workflows = collect_workflows(tmp_path, logger)
    workflow_map = build_workflow_map(workflows)
    graph = build_graph(workflows, workflow_map)

    dot = graph.to_string()
    assert 'label="Workflow A"' in dot
    assert 'label="Workflow B"' in dot
    assert 'label="call_b"' in dot


def test_job_needs_edges(tmp_path: Path) -> None:
    workflow = tmp_path / "ci.yml"
    workflow.write_text(
        """
name: CI
on: [push]
jobs:
  build:
    runs-on: ubuntu-latest
  test:
    runs-on: ubuntu-latest
    needs: build
""".strip(),
        encoding="utf-8",
    )

    logger = configure_logging(False)
    workflows = collect_workflows(tmp_path, logger)
    workflow_map = build_workflow_map(workflows)
    graph = build_graph(workflows, workflow_map)

    dot = graph.to_string()
    assert "label=needs" in dot


def test_collect_workflows_with_patterns(tmp_path: Path) -> None:
    workflow_a = tmp_path / "some-prefix-ci.yaml"
    workflow_b = tmp_path / "other.yml"

    workflow_a.write_text(
        """
name: Workflow A
on: [push]
jobs:
  build:
    runs-on: ubuntu-latest
""".strip(),
        encoding="utf-8",
    )

    workflow_b.write_text(
        """
name: Workflow B
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
""".strip(),
        encoding="utf-8",
    )

    logger = configure_logging(False)
    workflows = collect_workflows(tmp_path, logger, patterns=("some-prefix*.yaml",))

    assert [workflow.name for workflow in workflows] == ["Workflow A"]


def test_collect_workflows_with_exclude_glob(tmp_path: Path) -> None:
    workflow_a = tmp_path / "ci.yaml"
    workflow_b = tmp_path / "ci-legacy.yml"

    workflow_a.write_text(
        """
name: Workflow A
on: [push]
jobs:
  build:
    runs-on: ubuntu-latest
""".strip(),
        encoding="utf-8",
    )

    workflow_b.write_text(
        """
name: Workflow B
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
""".strip(),
        encoding="utf-8",
    )

    logger = configure_logging(False)
    workflows = collect_workflows(
        tmp_path,
        logger,
        exclude_globs=("*-legacy.yml",),
    )

    assert [workflow.name for workflow in workflows] == ["Workflow A"]


if __name__ == "__main__":
    main()

#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.14"
# dependencies = [
#   "structlog>=24.0.0",
#   "PyYAML>=6.0.0",
#   "Pillow>=10.3.0",
# ]
# ///
"""Convert page bundle images to webp and update front matter."""

from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

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

try:
    from PIL import Image, UnidentifiedImageError
except (
    ModuleNotFoundError
) as exc:  # pragma: no cover - dependency should be installed in CI
    raise SystemExit(
        "Missing dependency 'Pillow'. "
        "Install it (e.g. `pip install pillow`) or run via a PEP-723 aware runner (e.g. `uv run`)."
    ) from exc


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".svg"}


class FrontMatterError(ValueError):
    pass


@dataclass
class ProcessingStats:
    files_processed: int = 0
    images_converted: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FrontMatterBlock:
    data: dict[str, Any]
    start_line: int
    end_line: int
    block_text: str
    newline: str
    trailing_newline: bool
    lines: list[str]


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
    return structlog.get_logger("ci.convert_page_images")


def _detect_newline(text: str) -> str:
    return "\r\n" if "\r\n" in text else "\n"


def _parse_front_matter(md_text: str) -> FrontMatterBlock | None:
    lines = md_text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None

    end = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end = idx
            break
    if end is None:
        raise FrontMatterError(
            "Front matter starts with '---' but no closing '---' found."
        )

    block_text = "\n".join(lines[1:end])
    if block_text.strip():
        try:
            data = yaml.safe_load(block_text)
        except yaml.YAMLError as exc:
            raise FrontMatterError("Front matter YAML failed to parse.") from exc
    else:
        data = {}

    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise FrontMatterError("Front matter YAML must be a mapping.")

    return FrontMatterBlock(
        data=data,
        start_line=0,
        end_line=end,
        block_text=block_text,
        newline=_detect_newline(md_text),
        trailing_newline=md_text.endswith(("\n", "\r\n")),
        lines=lines,
    )


def _iter_index_files(root: Path) -> Iterable[Path]:
    yield from sorted(root.rglob("index.md"))


def _collect_image_paths(value: Any) -> list[str]:
    paths: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for item in node.values():
                walk(item)
            return
        if isinstance(node, (list, tuple)):
            for item in node:
                walk(item)
            return
        if isinstance(node, str):
            candidate = node.strip()
            if _is_local_image_path(candidate):
                paths.append(candidate)

    walk(value)
    seen: set[str] = set()
    unique: list[str] = []
    for item in paths:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def _is_local_image_path(value: str) -> bool:
    if not value:
        return False
    lowered = value.lower()
    if "://" in lowered or lowered.startswith("data:"):
        return False
    suffix = Path(lowered).suffix
    if suffix not in IMAGE_EXTENSIONS:
        return False
    return True


def _resolve_image_path(value: str, *, index_md: Path, repo_root: Path) -> Path:
    if value.startswith("/"):
        return repo_root / value.lstrip("/")
    candidate = index_md.parent / value
    if candidate.exists():
        return candidate
    fallback = repo_root / value
    if fallback.exists():
        return fallback
    return candidate


def _convert_to_webp(
    source_path: Path,
    target_path: Path,
    *,
    quality: int,
) -> None:
    if source_path.suffix.lower() == ".svg":
        raise ValueError("SVG conversion is not supported by Pillow.")
    target_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with Image.open(source_path) as image:
            image.load()
            if image.mode not in {"RGB", "RGBA"}:
                image = image.convert("RGBA" if "transparency" in image.info else "RGB")
            image.save(
                target_path,
                format="WEBP",
                quality=quality,
                method=6,
            )
    except UnidentifiedImageError as exc:
        raise ValueError("Unsupported image format for conversion.") from exc


def _build_updated_text(
    front_matter: FrontMatterBlock,
    replacements: dict[str, str],
) -> str | None:
    updated_block = front_matter.block_text
    for old, new in replacements.items():
        updated_block = updated_block.replace(old, new)

    if updated_block == front_matter.block_text:
        return None

    new_lines = (
        front_matter.lines[:1]
        + updated_block.splitlines()
        + front_matter.lines[front_matter.end_line :]
    )
    newline = front_matter.newline
    updated_text = newline.join(new_lines)
    if front_matter.trailing_newline and not updated_text.endswith(newline):
        updated_text += newline
    return updated_text


def _process_index_file(
    index_md: Path,
    *,
    repo_root: Path,
    quality: int,
    log: structlog.stdlib.BoundLogger,
    stats: ProcessingStats,
) -> None:
    stats.files_processed += 1
    try:
        md_text = index_md.read_text(encoding="utf-8")
    except OSError as exc:
        stats.errors.append(f"{index_md}: failed to read ({exc})")
        log.error("failed to read file", path=str(index_md), error=str(exc))
        return

    try:
        front_matter = _parse_front_matter(md_text)
    except FrontMatterError as exc:
        stats.errors.append(f"{index_md}: front matter error ({exc})")
        log.error("front matter parse error", path=str(index_md), error=str(exc))
        return

    if front_matter is None:
        log.info("no front matter found", path=str(index_md))
        return

    image_paths = _collect_image_paths(front_matter.data)
    if not image_paths:
        return

    replacements: dict[str, str] = {}
    originals_to_delete: list[Path] = []

    for image_path in image_paths:
        suffix = Path(image_path).suffix.lower()
        if suffix == ".webp":
            continue
        if suffix not in IMAGE_EXTENSIONS:
            continue

        source_path = _resolve_image_path(
            image_path, index_md=index_md, repo_root=repo_root
        )
        if not source_path.exists():
            stats.errors.append(f"{index_md}: missing image file '{image_path}'")
            log.error(
                "missing image file",
                path=str(index_md),
                image=str(image_path),
            )
            continue

        target_path = source_path.with_suffix(".webp")
        try:
            converted = False
            if not target_path.exists():
                _convert_to_webp(source_path, target_path, quality=quality)
                converted = True
            replacements[image_path] = str(Path(image_path).with_suffix(".webp"))
            originals_to_delete.append(source_path)
            if converted:
                stats.images_converted += 1
        except Exception as exc:
            stats.errors.append(f"{index_md}: failed to convert '{image_path}' ({exc})")
            log.error(
                "image conversion failed",
                path=str(index_md),
                image=str(image_path),
                error=str(exc),
            )

    if not replacements:
        return

    updated_text = _build_updated_text(front_matter, replacements)
    if updated_text is None:
        stats.errors.append(
            f"{index_md}: failed to update front matter for replacements"
        )
        log.error(
            "front matter update failed",
            path=str(index_md),
            replacements=replacements,
        )
        return

    try:
        index_md.write_text(updated_text, encoding="utf-8")
    except OSError as exc:
        stats.errors.append(f"{index_md}: failed to write ({exc})")
        log.error("failed to write file", path=str(index_md), error=str(exc))
        return

    for original in originals_to_delete:
        try:
            original.unlink()
        except OSError as exc:
            stats.errors.append(f"{index_md}: failed to delete '{original}' ({exc})")
            log.error(
                "failed to delete original image",
                path=str(index_md),
                image=str(original),
                error=str(exc),
            )


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Convert page bundle images to webp and update front matter.",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--root",
        type=Path,
        default=repo_root / "content",
        help="Root directory to search for index.md files.",
    )
    group.add_argument(
        "--file",
        type=Path,
        help="Process a single index.md file.",
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=80,
        help="WebP quality setting (1-100).",
    )
    return parser.parse_args(argv)


def _validate_quality(quality: int) -> int:
    if quality < 1 or quality > 100:
        raise ValueError("Quality must be between 1 and 100.")
    return quality


def main(argv: Sequence[str] | None = None) -> int:
    log = _configure_logging()
    repo_root = Path(__file__).resolve().parents[1]

    try:
        args = _parse_args(argv)
        quality = _validate_quality(args.quality)
    except Exception as exc:
        log.error("invalid arguments", error=str(exc))
        return 2

    stats = ProcessingStats()

    if args.file:
        index_md = args.file
        if not index_md.exists():
            log.error("index.md file does not exist", path=str(index_md))
            stats.errors.append(f"{index_md}: file does not exist")
        else:
            _process_index_file(
                index_md,
                repo_root=repo_root,
                quality=quality,
                log=log,
                stats=stats,
            )
    else:
        root = args.root
        if not root.exists():
            log.error("root directory does not exist", path=str(root))
            stats.errors.append(f"{root}: root directory does not exist")
        else:
            for index_md in _iter_index_files(root):
                _process_index_file(
                    index_md,
                    repo_root=repo_root,
                    quality=quality,
                    log=log,
                    stats=stats,
                )

    log.info(
        "conversion complete",
        files_processed=stats.files_processed,
        images_converted=stats.images_converted,
        errors=len(stats.errors),
    )

    if stats.errors:
        for message in stats.errors:
            log.warning("conversion issue", detail=message)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

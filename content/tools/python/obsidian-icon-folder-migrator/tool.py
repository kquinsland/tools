# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "click>=8.1",
#   "ruamel.yaml>=0.18",
#   "structlog>=24",
# ]
# ///
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Any, Literal

import click
import structlog
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

ICON_FRONTMATTER_KEY = "icon"
DEFAULT_DATA_JSON = ".obsidian/plugins/obsidian-icon-folder/data.json"
MissingBehavior = Literal["silent", "warn", "remove"]


yaml = YAML(typ="rt")
yaml.preserve_quotes = True
yaml.allow_unicode = True
yaml.default_flow_style = False


@dataclass(frozen=True)
class IconEntry:
    key: str
    icon: str
    note_path: Path


@dataclass(frozen=True)
class IconLoadResult:
    entries: list[IconEntry]
    missing_keys: set[str]


@dataclass(frozen=True)
class FrontmatterParts:
    frontmatter: str | None
    body: str


@dataclass(frozen=True)
class NoteUpdate:
    changed: bool
    removable: bool
    reason: str
    text: str


def configure_logging() -> None:
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
    )


def extract_icon(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, dict) and isinstance(value.get("iconName"), str):
        return value["iconName"]
    return None


def safe_relative_path(raw_path: str) -> Path | None:
    relative_path = Path(raw_path)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        return None
    return relative_path


def resolve_note_path(vault_root: Path, raw_path: str) -> Path | None:
    relative_path = safe_relative_path(raw_path)
    if relative_path is None:
        return None

    candidate = vault_root / relative_path

    if candidate.is_file() and candidate.suffix.lower() == ".md":
        return candidate

    if relative_path.suffix.lower() == ".md":
        return candidate if candidate.is_file() else None

    if candidate.is_dir():
        index_note = candidate / "index.md"
        if index_note.is_file():
            return index_note

    markdown_candidate = vault_root / f"{raw_path}.md"
    if markdown_candidate.is_file():
        return markdown_candidate

    return None


def split_frontmatter(text: str) -> FrontmatterParts:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return FrontmatterParts(frontmatter=None, body=text)

    for index, line in enumerate(lines[1:], start=1):
        if line.strip() in {"---", "..."}:
            return FrontmatterParts(
                frontmatter="".join(lines[1:index]),
                body="".join(lines[index + 1 :]),
            )

    return FrontmatterParts(frontmatter=None, body=text)


def load_frontmatter(frontmatter_text: str | None) -> CommentedMap:
    if frontmatter_text is None or not frontmatter_text.strip():
        return CommentedMap()

    loaded = yaml.load(frontmatter_text)
    if loaded is None:
        return CommentedMap()
    if not isinstance(loaded, CommentedMap):
        msg = "Frontmatter is not a YAML mapping"
        raise TypeError(msg)
    return loaded


def dump_frontmatter(frontmatter: CommentedMap) -> str:
    stream = StringIO()
    yaml.dump(frontmatter, stream)
    return stream.getvalue()


def dump_icon_line(icon: str) -> str:
    icon_frontmatter = CommentedMap()
    icon_frontmatter[ICON_FRONTMATTER_KEY] = icon
    return dump_frontmatter(icon_frontmatter)


def append_icon(frontmatter_text: str | None, icon: str) -> str:
    icon_line = dump_icon_line(icon)
    if frontmatter_text is None or not frontmatter_text:
        return icon_line
    if frontmatter_text.endswith(("\n", "\r")):
        return f"{frontmatter_text}{icon_line}"
    return f"{frontmatter_text}\n{icon_line}"


def replace_icon(frontmatter_text: str, frontmatter: CommentedMap, icon: str) -> str:
    icon_location = frontmatter.lc.key(ICON_FRONTMATTER_KEY)
    icon_line_index = icon_location[0]
    lines = frontmatter_text.splitlines(keepends=True)
    existing_line = lines[icon_line_index]
    base_indent = len(existing_line) - len(existing_line.lstrip(" "))

    end_line_index = icon_line_index + 1
    while end_line_index < len(lines):
        line = lines[end_line_index]
        stripped = line.strip()
        indent = len(line) - len(line.lstrip(" "))
        if stripped and not stripped.startswith("#") and indent <= base_indent:
            break
        end_line_index += 1

    return "".join(
        [
            *lines[:icon_line_index],
            dump_icon_line(icon),
            *lines[end_line_index:],
        ],
    )


def update_note_text(
    original_text: str,
    icon: str,
    *,
    update_existing: bool,
) -> NoteUpdate:
    parts = split_frontmatter(original_text)
    frontmatter = load_frontmatter(parts.frontmatter)

    if ICON_FRONTMATTER_KEY in frontmatter:
        current_icon = frontmatter[ICON_FRONTMATTER_KEY]
        if current_icon == icon:
            return NoteUpdate(
                changed=False,
                removable=True,
                reason="icon already matches",
                text=original_text,
            )
        if not update_existing:
            return NoteUpdate(
                changed=False,
                removable=False,
                reason="existing icon differs; use --update-existing to replace it",
                text=original_text,
            )

        rendered = render_note(
            parts, replace_icon(parts.frontmatter or "", frontmatter, icon)
        )
        return NoteUpdate(
            changed=rendered != original_text,
            removable=True,
            reason="updated existing icon",
            text=rendered,
        )

    rendered = render_note(parts, append_icon(parts.frontmatter, icon))
    return NoteUpdate(
        changed=rendered != original_text,
        removable=True,
        reason="added icon",
        text=rendered,
    )


def render_note(parts: FrontmatterParts, frontmatter_text: str) -> str:
    body = parts.body
    if parts.frontmatter is None and body:
        return f"---\n{frontmatter_text}---\n\n{body}"
    return f"---\n{frontmatter_text}---\n{body}"


def load_icon_entries(
    data: dict[str, Any],
    *,
    vault_root: Path,
    missing_behavior: MissingBehavior,
    log: structlog.stdlib.BoundLogger,
) -> IconLoadResult:
    entries: list[IconEntry] = []
    missing_keys: set[str] = set()

    for key, value in data.items():
        if key == "settings":
            continue

        icon = extract_icon(value)
        if icon is None:
            log.warning("Skipping entry without a usable icon", key=key)
            continue

        note_path = resolve_note_path(vault_root, key)
        if note_path is None:
            missing_keys.add(key)
            if missing_behavior == "warn":
                log.warning("No existing note file found for data.json key", key=key)
            continue

        entries.append(IconEntry(key=key, icon=icon, note_path=note_path))

    return IconLoadResult(entries=entries, missing_keys=missing_keys)


def write_data_json(data_json_path: Path, data: dict[str, Any]) -> None:
    data_json_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


@click.command()
@click.option(
    "--vault-root",
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
    default=Path("."),
    show_default=True,
    help="Path to the Obsidian vault root.",
)
@click.option(
    "--data-json",
    "data_json_path",
    type=click.Path(path_type=Path, file_okay=True, dir_okay=False),
    default=Path(DEFAULT_DATA_JSON),
    show_default=True,
    help="Path to obsidian-icon-folder data.json.",
)
@click.option(
    "--on-missing",
    type=click.Choice(["silent", "warn", "remove"], case_sensitive=False),
    default="warn",
    show_default=True,
    help="How to handle a data.json key that does not resolve to an existing note.",
)
@click.option(
    "--update-existing",
    is_flag=True,
    default=False,
    show_default=True,
    help="Replace an existing frontmatter icon value when it differs.",
)
@click.option(
    "--dry-run/--no-dry-run",
    default=True,
    show_default=True,
    help="Show planned changes without writing files.",
)
@click.option(
    "--remove-from-json",
    is_flag=True,
    default=False,
    show_default=True,
    help="Remove migrated entries from data.json after the note is updated or already matches.",
)
def main(
    vault_root: Path,
    data_json_path: Path,
    on_missing: MissingBehavior,
    update_existing: bool,
    dry_run: bool,
    remove_from_json: bool,
) -> None:
    """Move obsidian-icon-folder icon values into note frontmatter."""
    configure_logging()
    log = structlog.get_logger()

    vault_root = vault_root.expanduser().resolve()
    data_json_path = data_json_path.expanduser()
    if not data_json_path.is_absolute():
        data_json_path = vault_root / data_json_path
    data_json_path = data_json_path.resolve()

    data = json.loads(data_json_path.read_text(encoding="utf-8"))
    load_result = load_icon_entries(
        data,
        vault_root=vault_root,
        missing_behavior=on_missing,
        log=log,
    )
    entries = load_result.entries

    entries_by_note: dict[Path, list[IconEntry]] = defaultdict(list)
    for entry in entries:
        entries_by_note[entry.note_path].append(entry)

    changed_notes = 0
    removable_keys: set[str] = set()
    skipped_notes = 0

    for note_path, note_entries in entries_by_note.items():
        icons = {entry.icon for entry in note_entries}
        relative_note = note_path.relative_to(vault_root)

        if len(icons) > 1:
            skipped_notes += 1
            log.warning(
                "Skipping note because multiple data.json keys resolve to it with different icons",
                note=str(relative_note),
                keys=[entry.key for entry in note_entries],
                icons=sorted(icons),
            )
            continue

        icon = note_entries[0].icon
        original_text = note_path.read_text(encoding="utf-8")

        try:
            update = update_note_text(
                original_text,
                icon,
                update_existing=update_existing,
            )
        except ValueError as error:
            skipped_notes += 1
            log.warning(
                "Skipping note",
                note=str(relative_note),
                reason=str(error),
            )
            continue

        if update.changed:
            changed_notes += 1
            if dry_run:
                log.info(
                    "Would update note frontmatter",
                    note=str(relative_note),
                    icon=icon,
                    reason=update.reason,
                )
            else:
                note_path.write_text(update.text, encoding="utf-8")
                log.info(
                    "Updated note frontmatter",
                    note=str(relative_note),
                    icon=icon,
                    reason=update.reason,
                )
        else:
            if update.removable:
                log.info(
                    "No note change needed",
                    note=str(relative_note),
                    icon=icon,
                    reason=update.reason,
                )
            else:
                skipped_notes += 1
                log.warning(
                    "Skipping note",
                    note=str(relative_note),
                    icon=icon,
                    reason=update.reason,
                )

        if update.removable:
            removable_keys.update(entry.key for entry in note_entries)

    missing_keys_to_remove = (
        load_result.missing_keys if on_missing == "remove" else set()
    )
    data_json_keys_to_remove: set[str] = set()
    if remove_from_json:
        data_json_keys_to_remove.update(removable_keys)
    data_json_keys_to_remove.update(missing_keys_to_remove)

    if data_json_keys_to_remove:
        if dry_run:
            log.info(
                "Would remove entries from data.json",
                count=len(data_json_keys_to_remove),
                migrated_count=len(removable_keys) if remove_from_json else 0,
                missing_count=len(missing_keys_to_remove),
                keys=sorted(data_json_keys_to_remove),
            )
        else:
            for key in data_json_keys_to_remove:
                data.pop(key, None)
            write_data_json(data_json_path, data)
            log.info(
                "Removed entries from data.json",
                count=len(data_json_keys_to_remove),
                migrated_count=len(removable_keys) if remove_from_json else 0,
                missing_count=len(missing_keys_to_remove),
                path=str(data_json_path.relative_to(vault_root)),
            )

    log.info(
        "Finished",
        changed_notes=changed_notes,
        skipped_notes=skipped_notes,
        removable_migrated_data_json_entries=len(removable_keys),
        missing_data_json_entries=len(load_result.missing_keys),
        dry_run=dry_run,
    )


if __name__ == "__main__":
    main()

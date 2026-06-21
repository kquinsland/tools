---
date: 2026-06-21
draft: false
title: "Obsidian Icon Folder Migrator"
description: "Move Obsidian Icon Folder plugin icon assignments from data.json into note YAML frontmatter."
bookToc: false

resources:
  - name: tool-file
    src: tool.py
  - name: tool-icon
    src: images/tool-icon.svg

tags:
  - obsidian
  - markdown
  - yaml
  - frontmatter
  - migration
  - python
---

# Obsidian Icon Folder Migrator

{{< tool-image >}}

Migrate icon assignments from the old Obsidian Icon Folder plugin data file into each note's YAML frontmatter.
The tool reads `.obsidian/plugins/obsidian-icon-folder/data.json`, resolves each vault-relative entry to an existing Markdown note, and adds `icon: ...` to that note.

It is designed for cautious cleanup work: dry-run is the default, files are never created or moved, existing `icon` values are preserved unless you explicitly pass `--update-existing`, and successfully migrated JSON entries can optionally be removed with `--remove-from-json`.

## Example Usage

```shell
{{< py-usage >}}
```

```shell
# Preview what would change in the current directory vault.
uv run ./tool.py --vault-root ~/Notes

# Write note frontmatter updates after reviewing the dry run.
uv run ./tool.py --vault-root ~/Notes --no-dry-run

# Replace differing existing frontmatter icon values.
uv run ./tool.py --vault-root ~/Notes --update-existing --no-dry-run

# Remove data.json entries after they are migrated or already match.
uv run ./tool.py --vault-root ~/Notes --remove-from-json --no-dry-run

# Also remove data.json keys that no longer resolve to notes.
uv run ./tool.py --vault-root ~/Notes --on-missing remove --remove-from-json --no-dry-run
```

## Behavior

- Reads string icon values and object values with `iconName`.
- Resolves note paths directly, folder paths through `index.md`, and extensionless paths through `<path>.md`.
- Adds `icon` as the last frontmatter key when it is missing.
- Leaves an existing matching `icon` untouched.
- Skips a differing existing `icon` unless `--update-existing` is passed.
- Skips unsafe absolute paths and paths containing `..`.

## Dependencies

{{< tool-dependencies >}}

## Changelog

{{< tool-changelog >}}

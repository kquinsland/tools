---
date: 2026-03-02
draft: false
title: 'Sync Conflict Triage'
description: 'Scan a folder for SyncThing-style conflict files, compare side-by-side, edit in place, and stage deletions safely.'

resources:
  - name: tool-file
    src: tool.html
  - name: tool-icon
    src: images/tool-icon.svg

tags:
  - html
  - files
  - syncthing
  - diff
  - conflict
  - triage
---
# Sync Conflict Triage

{{< tool-image >}}

Scan a directory for SyncThing-style conflict files, triage one conflict group at a time with side-by-side diffs, edit files in place, and stage deletions for review before applying.

{{< tool-link link_text="Open the tool" >}}

## Notes

- Uses the File System Access API (`showDirectoryPicker`) to read and edit local files.
- Files are only deleted after explicit confirmation in the deletion review pane.

## Dependencies

{{< tool-dependencies >}}

## Changelog

{{< tool-changelog >}}

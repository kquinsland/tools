---
date: 2026-01-30
draft: false
title: 'YAML ↔ JSON Convert & Compare'
description: 'Convert YAML, JSON, JSONC, and JSON5 documents, or compare two files for logical equality with formatting controls.'

resources:
  - name: tool-file
    src: tool.html
  - name: tool-icon
    src: images/tool-icon.svg

tags:
  - html
  - yaml
  - json
  - jsonc
  - json5
  - convert
  - compare
---
# YAML ↔ JSON Convert & Compare

{{< tool-image >}}

Convert YAML to JSON or JSON/JSONC/JSON5 to YAML, or compare two documents for logical equality. Includes formatting controls, copy/save actions, and shareable state.

{{< tool-link link_text="Open the tool" >}}

## Notes

- YAML comments are ignored during conversion.
- JSONC/JSON5 comments are ignored during conversion.
- Formatted JSON output is strict JSON, even when the input used JSONC or JSON5 features.
- Multiple YAML documents in a single file are rejected.

## Dependencies

{{< tool-dependencies >}}

## Changelog

{{< tool-changelog >}}

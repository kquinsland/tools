---
date: 2026-07-20
draft: false
title: 'Salt State Graph'
description: 'Paste or open Salt highstate JSON and explore its requisite graph entirely in your browser.'

resources:
  - name: tool-file
    src: tool.html
  - name: tool-icon
    src: images/tool-icon.svg

tags:
  - html
  - salt
  - highstate
  - graph
  - dependencies
  - json
---
# Salt State Graph

{{< tool-image >}}

Paste, select, or drop JSON from Salt's `state.show_highstate` or
`state.show_sls` output to build an interactive requisite graph. Input stays in
your browser and is never uploaded or saved.

{{< tool-link link_text="Open the tool" >}}

## Features

- Supports typed, module-less, SLS, glob, and `_in` requisites.
- Handles `__extend__` declarations and output containing multiple minions.
- Fuzzy-searches states and filters by minion, connection status, or requisite family.
- Loads smaller inputs directly from a local-only `#state=<base64>` URL fragment.
- Downloads the visible graph as SVG, PNG, WebP, DOT, or normalized JSON.
- Uses browser-native JavaScript and SVG with no external dependencies.

## Dependencies

{{< tool-dependencies >}}

## Changelog

{{< tool-changelog >}}

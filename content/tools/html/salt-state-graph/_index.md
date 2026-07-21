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
`state.show_sls` output to build an interactive requisite graph. Smaller inputs
and their active filters are mirrored into the URL fragment so the graph can be
shared or bookmarked.

{{< tool-link link_text="Open the tool" >}}

## Features

- Supports typed, module-less, SLS, glob, and `_in` requisites.
- Handles `__extend__` declarations and output containing multiple minions.
- Fuzzy-searches states and filters by minion, connection status, or requisite family.
- Automatically saves smaller valid inputs and active filters in a shareable URL fragment.
- Opens the source state JSON, including matching `__extend__` blocks, when a node is selected.
- Downloads the visible graph as SVG, PNG, WebP, DOT, or normalized JSON.
- Uses browser-native JavaScript and SVG with no external dependencies.

## Dependencies

{{< tool-dependencies >}}

## Changelog

{{< tool-changelog >}}

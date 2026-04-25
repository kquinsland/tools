---
date: 2026-04-25
draft: false
title: 'EXIF Inspector'
description: 'Inspect EXIF and related image metadata locally in the browser with drag-and-drop support.'
resources:
  - name: tool-file
    src: tool.html
  - name: tool-icon
    src: images/tool-icon.svg
dependencies:
  - package: exifr
    via: https://github.com/MikeKovarik/exifr
    version: 7.1.3

tags:
  - html
  - image
  - exif
  - metadata
  - photography
---
# EXIF Inspector

{{< tool-image >}}

Drop an image file to inspect EXIF and related metadata locally in your browser. The tool keeps processing on-device, shows grouped or flat views, and can export the parsed metadata as JSON.

{{< tool-link link_text="Open the tool" >}}

## Dependencies

{{< tool-dependencies >}}

## Changelog

{{< tool-changelog >}}

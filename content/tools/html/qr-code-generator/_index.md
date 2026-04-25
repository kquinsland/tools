---
date: 2026-04-25
draft: false
title: 'QR Code Generator'
description: 'Generate QR codes entirely in your browser, including calendar tasks and common share formats.'
resources:
  - name: tool-file
    src: tool.html
  - name: tool-icon
    src: images/tool-icon.svg
dependencies:
  - package: qrcode
    via: https://cdn.jsdelivr.net/npm/qrcode@1.5.4/+esm
    version: 1.5.4

tags:
  - html
  - qr
  - qrcode
  - calendar
  - offline
---
# QR Code Generator

{{< tool-image >}}

Generate QR codes directly in your browser without any backend requests. Includes quick templates for text, URLs, contacts, Wi-Fi, email, calendar events, and calendar tasks.

{{< tool-link link_text="Open the tool" >}}

## Dependencies

{{< tool-dependencies >}}

## Changelog

{{< tool-changelog >}}

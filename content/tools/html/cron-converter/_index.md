---
date: 2026-02-13
draft: false
title: 'Cron Timezone Converter'
description: 'Convert POSIX 5-field cron schedules between timezones, including day/hour wrap-around handling.'
resources:
  - name: tool-file
    src: tool.html
  - name: tool-icon
    src: images/tool-icon.svg

tags:
  - html
  - cron
  - timezone
  - scheduling
  - convert
---
# Cron Timezone Converter

{{< tool-image >}}

Convert a POSIX 5-field cron expression from one timezone to another. The tool handles weekday/day-boundary rollover and can output split expressions for engines that do not support wrap-around hour ranges.

{{< tool-link link_text="Open the tool" >}}

## Notes

- Supports POSIX 5-field syntax (`minute hour day-of-month month day-of-week`).
- Day-of-week accepts `0-7`; `0` and `7` are both treated as Sunday.
- Conversion output is generated for the weekly-style case where `day-of-month` and `month` are `*`.
- The calendar preview is a fixed Monday-Sunday grid with overlap coloring.

## Dependencies

{{< tool-dependencies >}}

## Changelog

{{< tool-changelog >}}

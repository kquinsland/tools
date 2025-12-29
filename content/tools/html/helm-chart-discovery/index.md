---
date: 2025-12-21
draft: false
title: 'Helm Chart Discovery'
description: 'Fetch a Helm repository index.yaml or OCI chart reference to explore chart metadata with search and filters.'
resources:
  - name: tool-file
    src: tool.html
    # Made available for use below
  - name: tool-icon
    src: images/tool-image.webp

tags:
  - helm
  - charts
  - html
  - discover
  - search
---
# Helm Chart Discovery

{{< tool-image >}}

Paste a Helm repository URL (or just the domain), load a local `index.yaml` file, or use an OCI
reference like `oci://registry.example.com/namespace/chart`.
This tool fetches and parses chart metadata so you can quickly scan charts, versions, and metadata.

{{< tool-link link_text="Open the tool" >}}.

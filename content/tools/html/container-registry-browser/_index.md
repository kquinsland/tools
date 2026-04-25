---
date: 2026-04-25
draft: false
title: 'Container Registry Browser'
description: 'Browse OCI and Docker Registry HTTP API v2 repositories, tags, manifests, digests, platforms, and layers from the browser.'
resources:
  - name: tool-file
    src: tool.html
  - name: tool-icon
    src: images/tool-icon.svg

tags:
  - docker
  - oci
  - registry
  - containers
  - html
---
# Container Registry Browser

{{< tool-image >}}

Enter a container registry or repository URL to browse repositories where catalog access is
available, list tags, and inspect OCI/Docker manifests, platform entries, config digests, and
layers. The tool starts with anonymous requests, then tries anonymous bearer-token authorization
before asking for explicit credentials.

{{< tool-link link_text="Open the tool" >}}.

## Dependencies

{{< tool-dependencies >}}

## Changelog

{{< tool-changelog >}}

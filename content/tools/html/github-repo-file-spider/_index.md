---
date: 2026-02-11
draft: false
title: 'GitHub Repo File Spider'
description: 'Scan GitHub repositories for one or more files and report match stats at org/user scale.'

resources:
    - name: tool-file
      src: tool.html
    - name: tool-icon
      src: images/tool-icon.svg

tags:
  - github
  - file-check
  - metadata
  - repository
  - html
---
# GitHub Repo File Spider

{{< tool-image >}}

Scan a GitHub repo, user, or organization for required files (for example
`renovate.json` or `.github/CODEOWNERS`) and get fast match stats.

{{< tool-link link_text="Open the tool" >}}.

## What It Checks

- Target: one repo (`owner/repo`) or all accessible repos under a user/org.
- File set: comma/newline separated paths.
- Policy mode:
  - `Any file` means at least one listed file marks a repo as matched.
  - `All files` means every listed file must exist for a match.

## Personal access tokens (PATs)

GitHub API limits unauthenticated requests quickly. Provide a PAT when scanning
larger orgs or private repos.

- Token is stored only in `localStorage` on your browser.
- Use the tool's `Clear token` button to remove it.
- Token is never written into the URL state.

## Dependencies

{{< tool-dependencies >}}

## Changelog

{{< tool-changelog >}}

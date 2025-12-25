---
date: 2025-12-25
draft: false
title: 'GitHub Actions Spider'
description: 'Crawl repositories and extract GitHub Actions uses-steps from workflow files.'

resources:
    - name: tool-file
      src: tool.html

    # Made available for use below
    - name: tool-icon
      src: images/tool-image.webp


tags:
  - github
  - actions
  - workflow
  - crawl
  - html
  - search
---
# GitHub Actions Spider

{{< tool-image >}}

Paste a GitHub URL (workflow file, repo, or user/org) and scan workflows for `uses` steps.
This tool crawls repos, extracts jobs + steps, and makes it easy to search or export the results.

{{< tool-link link_text="Open the tool" >}}.

## Personal access tokens (PATs)

GitHub's API is rate limited. If you hit limits or need access to private repos, provide a PAT.
The tool stores the token in `localStorage` on your device and sends it only to GitHub.

Basic steps to create a PAT:

1. Open GitHub settings → Developer settings → [Personal access tokens](https://github.com/settings/tokens).
2. Create a token with the minimum scopes you need (for public repos, `public_repo` is enough; for private repos, include `repo`).
3. Copy the token once and paste it into the tool's PAT field, then click “Save token”.

Use the “Clear token” button in the tool to remove it from `localStorage`.

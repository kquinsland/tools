# Tools

Inspired by [this post](https://simonwillison.net/2025/Dec/10/html-tools/), I've created my own take on the "static site as a public repository of simple browser-based tools".

This is powered by Hugo and the "rendered" site is hosted via [GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages) and made available at: [https://tools.karlquinsland.com](https://tools.karlquinsland.com).

## How it works

// TODO: llm diagram of the deploy process for GitHub Pages and add to this `readme.md`

## Developer workflow

This repo uses [`mise`](https://mise.jdx.dev/) for toolchain and task orchestration, with `uv` handling Python environments and dependencies.

Common commands:

- `mise install`: install the pinned CLI toolchain
- `mise run bootstrap`: install the toolchain and sync all Python dependency groups
- `mise run lint`: run the full pre-commit suite
- `mise run generate`: refresh `data/tools.yaml`, `static/tools.txt`, and per-tool changelogs
- `mise run site:build`: render the static site into `public/`
- `mise run site:serve`: run the local Hugo development server

## TODOs

- more/betteR  `CI` to get:
  - `playwright` setup for HTML tool testing
  - screenshot or similar tool to automated screenshotting of docs/tools for use in `data/tools.yaml` (for landing page cards)

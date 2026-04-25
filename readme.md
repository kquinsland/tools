# Tools

Inspired by [this post](https://simonwillison.net/2025/Dec/10/html-tools/), I've created my own take on the "static site as a public repository of simple browser-based tools".

This is powered by Hugo and the "rendered" site is hosted via [GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages) and made available at: [https://tools.karlquinsland.com](https://tools.karlquinsland.com).

## GitHub Actions release flow

The workflows under `.github/workflows/` are split into a few small pieces so the release pipeline can reuse the same build logic for both automated releases and manual recovery/testing.

### Validation on pull requests

- `ci_pre-commit.yaml` runs on pull requests targeting `main`.
- The `pre-commit` job executes `mise run lint`, which currently runs the full pre-commit suite via `uv run pre-commit run --all-files`.
- The `generated-files` job executes `mise run check:generated`, which regenerates derived site data and fails if tracked generated files such as `data/tools.yaml`, `static/tools.txt`, or per-tool changelogs are stale.
- This is the main gate for normal changes and also for the release PR that `release-please` opens.

### Release creation on `main`

- `release-please.yaml` runs on every push to `main`.
- It first reruns the generated-file check so a release cannot be cut from a commit with stale derived content.
- If that passes, the `release-please` job runs `googleapis/release-please-action` using `release-please-config.json` and `.release-please-manifest.json`.
- Release Please either updates or opens the release PR, and when a release is actually created it exposes the released commit SHA and tag as job outputs.

### Build and publish to GitHub Pages

- The `deploy-pages` job in `release-please.yaml` only runs when Release Please reports that a release was created.
- That job calls the reusable workflow in `pages.yaml`, passing the released commit SHA as the `ref` input so Pages is built from the exact released revision rather than whatever happens to be at the branch tip later.
- In `pages.yaml`, the `build` job checks out that ref, installs the pinned toolchain with `mise`, runs `mise run release:build-pages`, verifies generated files again through the task dependency, and then renders the site with `hugo --minify`.
- The built `public/` directory is uploaded as the Pages artifact, and the `deploy` job publishes that artifact with `actions/deploy-pages`.

### Supporting workflows

- `meta_zizmor.yaml` is a workflow-lint/security-analysis pass for GitHub Actions themselves. It runs when workflow files change, and can also be called manually or from another workflow.
- `meta_cleanup.yaml` is scheduled housekeeping that deletes older workflow runs to keep Actions history manageable.
- `pages.yaml` also supports `workflow_dispatch`, which provides a break-glass/manual redeploy path for a chosen ref without needing to cut a new release.

In practice, the release path is: open PR -> `ci_pre-commit.yaml` validates the change -> merge to `main` -> `release-please.yaml` decides whether a release should be cut -> on a real release, `pages.yaml` builds and deploys the released commit to GitHub Pages.

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

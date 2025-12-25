I need a single page HTML tool that can spider crawl github repos to extract each GH Action file and from each file, extract the step/`uses` entries.

The user should supply a URL in the form of either an action file or GH repo or a GH user/org.
Examples are provided below.

To facilitate this scan, a user may need to supply a PAT (personal access token) to avoid rate limiting and access private repos.
If the user does not do this (or there is no token found in local storage), the tool should proceed unauthenticated.
Near the top of the page there should be a simple status area that shows progress as repos are crawled and GH Action files are processed / indicate errors if any occur. (rate limit, auth token bad, repo not found, etc.)


Examples:

User provides: https://github.com/kquinsland/tmtdt-lite/blob/main/.github/workflows/meta_cleanup.yaml
Then do: This is an explicit path to a GH Action file in a repo, so crawl that single file and extract the relevant info.

User Provides: https://github.com/kquinsland/some-repo
Then do: This is an explicit GH repo, so crawl that single repo for GH Action files and extract the relevant info.

User Provides: https://github.com/kquinsland
Then do: This is a GH user/org, so first attempt to list all repos and display them. Give the user a simple checkbox for each repo and a "scan selected" button. Then crawl all selected repos for that user/org for GH Action files and extract the relevant info. This way, the user can select which repos to scan in the event that the org/user has many repos.


Since each tool.html has an `index.md` file, document the basics of getting a PAT from GH and storing it in local storage for the tool to use in the `index.md` file.

For each repo, display the following information in a table:

- File name of the action file (e.g. `.github/workflows/ci.yml`)
- Job name (e.g. `build`)
- Step name (e.g. `Checkout code`)
- Step ID (if any)
- `uses` entry (e.g. `actions/checkout@v2`)
  - Version information should be included to the greatest specificity available (e.g. commit SHA if present, else tag, else branch)

Ideally, that table would be collapsible to make it easier to navigate when there are many repos and many actions.
Similarly, a basic search/filter box would be helpful to quickly find relevant entries.

At the bottom of the page, in it's own collapsible section, render a simple YAML document/viewer that shows the raw extracted data in a structured format (e.g. an array of objects with the above fields). This makes it easy to copy/paste the data for further processing in more advanced tools. Data pasted into this section can be ignored by the tool itself.

Additional clarifications:

- The raw data view should support YAML and JSON formats with a toggle (default to YAML) and a single Copy button that copies the currently selected format.
- Raw data output should include a link to the workflow file in GitHub.
- Workflow file names in the results table should be clickable links to the corresponding file in GitHub.
- YAML parsing must handle unicode/emoji content in workflow files.
- Display GitHub rate limit headers if present (`x-ratelimit-*`), including time until reset, and log when the limit is reached.
- The status log should include a zero-padded 24-hour `HH:MM:SS` timestamp prefix on every line.
- The error badge should be a toggle that filters the log to show only error entries; place the toggle below the log so the status badges don't shift during scans.
- Layout tweaks: stack the URL input above the PAT input; place Save/Clear token buttons under the PAT input; arrange status badges on separate lines (phase, then rate limit, then counts).

The goal of this tool is to answer questions like:

- What repo(s) have an action with `Mattraks/delete-workflow-runs`?
  - What version of `Mattraks/delete-workflow-runs` is being used in each case?
  - What file / job / step is it used in?

- What repos have a `ci_release.yml` file?
- What repos have a step with `uses: actions/checkout`?

Due to the complexity of this tool, it is acceptable to use external libraries (e.g. for making GH API calls, for building the table UI, etc.), but the entire tool must still be a single HTML file that can be opened and run in a modern web browser without any server-side components.

General notes:

- the `gh` tool is in `$PATH`, you may use it to open a PR when the tool is complete.
- the `git` tool is in `$PATH`, please use it to create a new branch for your work. The branch name should follow the pattern `tool/<tool-name>`, e.g. `tool/github-action-spider`.

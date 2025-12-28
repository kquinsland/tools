I have created a git branch for you, please get right to work on:

The high level idea is to be able to present the user with their most commonly used tools.
The way to do this is to track page access per tool.

Keeping the number one directive / rule for this repo: local, self-contained, this means that there can be no remote server to send usage data to.
This means we need to store usage data locally on the user's machine.

Rather than duplicate code, it is possible to put a simple javascript snippet into the `static` directory that each tool can load to handle the tracking.

For example, the `static/test.js` file is accessible at `https://web-server-here.tld/test.js`.

To facilitate user management of this data, please also create a simple page at `static/analytics.html` that can read and display the usage data and export it.
As always, the user must be given a way to clear it it as well.


So the tasks are:

- Create `static/analytics.js` that tracks page access and stores it locally.
- Create `static/analytics.html` that reads, displays, exports, and clears the usage data.
- Update the skill/documentation around creating new tools to include loading the `analytics.js` file for tracking.
- Update existing tools to load the `analytics.js` file for tracking.


If possible, the analytics.js file should add a footer to each page that indicates tracking is enabled and links to the analytics.html page for user management of the data.
The footer should indicate the number of times the user has accessed that tool if possible.

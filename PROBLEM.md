Start by creating a new branch using the `tool/too-name-here` pattern.
When you are done, use the `gh` tool to create a pull request against the `main` branch.

The tool you are to build will be a HTML page meant to quickly facilitate working with URLs and Markdown links.

At the top of the page, the user will paste in text that may contain URLs .
Extract all URLs  from the text and display them in a list below the input area.
Disregard all other text.
Persist the raw input in either local storage or the URL hash so that if the user refreshes the page, their input is not lost and/or the state can be shared via URL.

In a second text area below the list of URLs, display a Markdown-formatted link for each URL, one per line.
The user should be able to toggle different options for the Markdown links, including:

- Link text: either the URL itself, or "Link" or the title of the webpage (fetched from the URL)
- Whether to open the link in a new tab (i.e., adding `target="_blank"` to the link)
- Weather to add a leading list item marker
- Weather to add a `[ ]` checkbox before each link

Each option should be a toggle.
When the user changes any of the options, the Markdown links should update automatically.

If the user chooses to use the webpage title as the link text, fetch the title asynchronously and update the Markdown links once the title is retrieved.

If there was an error fetching the title for a URL, use the URL itself as the link text for that URL.

There should be a button to copy the generated Markdown links to the clipboard.
The page should feature a console / log area at the bottom that displays any errors encountered during the fetching of webpage titles.

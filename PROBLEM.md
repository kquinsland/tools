Both the `gh` tool and the `git` tool are in $PATH.

Start by creating a new branch for this issue.
`tool/too-name-here`

When the tool is finished, create push the tested changed to the new branch and create a pull request targeting the `main` branch.

## Tool Functionality

This will be a HTML tool that allows the user to drag/drop a 3mf file into the browser window. The tool will parse the 3mf file and display all metadata associated with the file in addition to the list of the contained objects, along with their properties (e.g., name, size, color, etc.).

If thumbnails are present in the 3mf file, they should be displayed as well next to their associated objects or if the thumbnail is for the entire model, it should be displayed at the top of the page.

If practical, the tool should also allow the user to download individual objects from the 3mf file as separate files (e.g., STL or OBJ format).

Details on the 3mf file format can be found here: https://3mf.io/specification/

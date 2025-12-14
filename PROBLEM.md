Please fill in `ci/convert_page_images.py` with python code that does the following:

The tool is meant to parse the front-matter of every relevant index.md file.
It should look for any file that happens to be an image file (png, jpg, jpeg, gif, webp, avif, svg)
If it finds any image files that are not already `webp` format, it should convert them to the webp format.

The converted webp files should be saved in the same directory as the original image files and should have the same base name as the original file but with a .webp extension.

The front matter must then be updated to replace the original image file paths with the new webp file paths.
The tool should work in one of two modes:

- A recursive mode, where it searches through all subdirectories of a given root directory for index.md files and processes them accordingly.
- A single-file mode, where it processes only a specified index.md file.

The tool should have reasonable/sane defaults for CLI arguments, such as the root directory to start searching from and quality settings for the webp conversion.
The tool should also provide helpful error messages if it encounters issues, such as missing files or unsupported image formats.

## Example

Assuming the tool encounters a directory structure like this:

```shell
content/tools/html
├── hello-world
│   ├── images
│   │   └── tool-icon.png
│   ├── index.md
│   └── tool.html
└── _index.md
```

And the `content/tools/html/hello-world/index.md` file looks like this:

```markdown
---
date: 2025-12-17T18:02:54-08:00
draft: false
# This ends up in the <title> tag, not an automatic H1
title: 'Hello, World'
description: 'This is the first tool description here.'
# # Don't need a ToC for the single page
# bookToc: false


resources:
    # Made available for use below
    - name: tool-icon
      src: images/tool-icon.png

    - name: tool-file
      src: tool.html


# HugoBook theme does not really show these anywhere but can be useful metadata for searching/filtering
tags:
    - demo
    - html
    - basic
    - input
---
# Hello, World

This the the first tool.

This theme offers up a few different ways to link to tools.

Access it [here]({{< tool-link >}}).

or {{< tool-link link_text="here">}}.

{{<button href="tool.html">}}Open{{</button>}}

{{< tool-image >}}

// TODO: default scaling and sizing options for tool images?

```

Then the script should identify that the page bundle has two resources: `images/tool-icon.png` and `tool.html`.
Recognizing that `tool-icon.png` is an image file that is not already `webp` format, it should convert the `content/tools/html/hello-world/files/tool-icon.png` file to `content/tools/html/hello-world/files/tool-icon.webp` and update the front-matter of `content/tools/html/hello-world/index.md` to reflect this change, resulting in the following updated front-matter:

```markdown

---
# <... omitted for brevity ...>

resources:
    - name: tool-icon
      src: images/tool-icon.webp

    - name: tool-file
      src: tool.html

<... omitted for brevity ...>

---
# <... omitted for brevity ...>
```

The tool should make no other changes to the markdown content or front-matter.

The original file should be deleted only after the conversion and front matter update is successful.

Print out basic stats at the end, such as number of files processed, number of images converted, and any errors encountered.
Do not treat a front-mater parse error or file missing error or conversion error as a fatal error; continue processing other files.

## General Requirements

- Use Python 3.14.
- Use `ty` and `ruff` tools (already in $PATH) to check your code for type and linting issues before submitting.

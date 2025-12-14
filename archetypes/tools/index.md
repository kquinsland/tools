---
# This ends up in the <title> tag, not an automatic H1
title: "{{ .Name | humanize | title }}"
date: {{ .Date }}
draft: false

description: 'A brief description of the tool goes here.'

# We do not need to generate a ToC for a single tool's page unless there's actually a lot of documentation to accompany it
# bookToc: false

resources:
    # Required!
    - name: tool-file
      src: tool.html

    # Made available for use below
    - name: tool-icon
      src: images/tool-icon.webp

# HugoBook theme does not really show these anywhere but can be useful metadata for searching/filtering
tags:
    - html
---
# "{{ .Name | humanize | title }}"

//TODO: a brief description of the tool

Access it [here]({{< tool-link >}}) or {{<button href="tool.html">}}Open{{</button>}}

{{< tool-image >}}

//TODO: any documentation about the tool goes here

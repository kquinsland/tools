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
      src: images/tool-icon.webp

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

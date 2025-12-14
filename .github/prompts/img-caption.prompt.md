---
mode: 'agent'
tools: ['read_file', 'write_file', 'read_file', 'edit_file', 'explain_code', 'replace_string_in_file','search_workspace']
---
<!-- markdownlint-disable-file -->
For the active markdown file, extract each image featured in the front matter under the `resources` key.
Open each image file and describe the image in the `caption` and `alt` field.

If you encountered this front matter in a markdown file:
```yaml
resources:
  - src: images/oem01.webp
    name: oem01
    params:
      caption: ""
      alt: ""
      attr: ""
```

You would open the file `images/oem01.webp` and describe the image in the `caption` and `alt` fields.

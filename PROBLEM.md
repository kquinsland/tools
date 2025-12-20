Please take a look at the shortcode that is used on the front page.
It renders out cards featuing the newest tools.

There's a small issue with certain strings.
Given this snip from data/tools.yaml:

```yaml
  - html/url-inspect-rewrite:
      title: "URL Inspect & Rewrite"
      language: "html"
      description: "Parse a URL, review query parameters, and rebuild a cleaner link."
      toolbox:
        file: "tool.html"
        introduced_commit: null
        updated_commit: null
      tags:
        - "html"
        - "url"
        - "query"
        - "privacy"
        - "cleanup"
```

Please make sure that the title "URL Inspect & Rewrite" is rendered correctly on the card!

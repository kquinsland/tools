{{- $title := or .Title .LinkTitle .Site.Title (path.Base (strings.TrimSuffix "/" .RelPermalink) | humanize | title) -}}

# {{ $title }}

{{ with .Description }}{{ . }}

{{ end -}}
Canonical: {{ .Permalink }}
{{ if not .Date.IsZero }}Published: {{ .Date.Format "2006-01-02" }}
{{ end -}}
{{ if not .Lastmod.IsZero }}Updated: {{ .Lastmod.Format "2006-01-02" }}
{{ end -}}
{{ with .Params.tags }}Tags: {{ delimit . ", " }}
{{ end }}

---

{{ $content := .RenderShortcodes -}}
{{ $content = replaceRE `(?m)^[[:space:]]*</?div[^>]*>[[:space:]]*$` "" $content -}}
{{ $content = replaceRE `<a[[:space:]]+href="([^"]+)"[^>]*>([^<]+)</a[[:space:]]*>` `[$2]($1)` $content -}}
{{ $content = replaceRE `[[:space:]]*\{anchor=false\}` "" $content -}}
{{ $content }}

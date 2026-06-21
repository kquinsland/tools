{{- $changelog := .Page.Resources.GetMatch "changelog.md" -}}
{{- $file := .Get "file" | default "changelog.md" -}}
{{- $raw := "" -}}
{{- if $changelog -}}
{{- $raw = $changelog.RawContent | strings.TrimSpace -}}
{{- else if $file -}}
{{- $path := path.Join .Page.File.Dir $file -}}
{{- $raw = readFile $path | strings.TrimSpace -}}
{{- end -}}
{{- if $raw -}}
{{- $raw = replaceRE `(?s)^---\n.*?\n---(?:\n|$)` "" $raw | strings.TrimSpace -}}
{{- end -}}
{{- if not $raw -}}
No changelog entries yet.
{{- else -}}
{{- $raw = $raw | strings.TrimPrefix "## " -}}
{{- $entries := split $raw "\n## " -}}
{{- $last := .Get "last" | default 2 | int -}}
{{- $max := math.Min $last (len $entries) -}}
{{- range $i, $entry := $entries -}}
{{- if lt $i $max }}

## {{ $entry }}

{{- end -}}
{{- end -}}
{{- if not (.Get "nolink") -}}
{{- $full := "" -}}
{{- $pagePath := printf "%s/changelog" .Page.Path -}}
{{- with .Site.GetPage $pagePath -}}
{{- with .OutputFormats.Get "markdown" -}}
{{- $full = .Permalink -}}
{{- else -}}
{{- $full = .Permalink -}}
{{- end -}}
{{- end -}}
{{- if not $full -}}
{{- $full = printf "%schangelog/" .Page.Permalink -}}
{{- end -}}
{{- $count := len $entries -}}
{{- $label := cond (eq $count 1) "commit" "commits" }}

[View full changelog ({{ $count }} {{ $label }})]({{ $full }})
{{- end -}}
{{- end -}}

{{- $tools := site.Data.tools.tools -}}
{{- $category := lower (default "" (.Get "category")) -}}
{{- $hasTools := false -}}

{{- if not $tools -}}
No tools available yet.
{{- else -}}
{{- range $item := $tools -}}
{{- range $slug, $tool := $item -}}
{{- $language := lower (default "" $tool.language) -}}
{{- if and $category (not (or (eq $language $category) (hasPrefix $slug (printf "%s/" $category)))) -}}
{{- continue -}}
{{- end -}}
{{- $hasTools = true -}}
{{- $page := site.GetPage (printf "/tools/%s" $slug) -}}
{{- $href := printf "%stools/%s/" site.BaseURL $slug -}}
{{- if $page -}}
{{- with $page.OutputFormats.Get "markdown" -}}
{{- $href = .Permalink -}}
{{- else -}}
{{- $href = $page.Permalink -}}
{{- end -}}
{{- end }}

- [{{ default $slug $tool.title }}]({{ $href }}){{ with $tool.description }}: {{ . }}{{ end }}
{{- end -}}
{{- end -}}
{{- if not $hasTools }}
No tools found{{ if $category }} in {{ $category }}{{ end }}.
{{- end -}}
{{- end -}}

{{- $stats := site.Data.tools.stats | default dict -}}
{{- $groups := $stats.dependency_tools_by_language | default (slice) -}}

{{- range $group := $groups }}

### {{ title $group.language }}

{{- range $tool := $group.tools -}}
{{- $deps := $tool.dependencies | default (slice) -}}
{{- $page := site.GetPage (printf "/tools/%s" $tool.slug) -}}
{{- $href := printf "%stools/%s/" site.BaseURL $tool.slug -}}
{{- if $page -}}
{{- with $page.OutputFormats.Get "markdown" -}}
{{- $href = .Permalink -}}
{{- else -}}
{{- $href = $page.Permalink -}}
{{- end -}}
{{- end }}

#### [{{ $tool.title }}]({{ $href }})

This tool relies on {{ len $deps }} dependencies.

| # | Library | Version | Via |
| ---: | --- | --- | --- |
{{- range $idx, $dep := $deps }}
{{- $package := $dep.package | default "" -}}
{{- $version := $dep.version | default "-" -}}
{{- $via := $dep.via | default "-" -}}
{{- $viaText := $via -}}
{{- if ne $via "-" -}}
{{- with (urls.Parse $via) -}}
{{- if .Host -}}{{- $viaText = .Host -}}{{- end -}}
{{- end -}}
{{- end }}
| {{ add $idx 1 }} | {{ $package }} | {{ $version }} | {{ if ne $via "-" }}[{{ $viaText }}]({{ $via }}){{ else }}-{{ end }} |
{{- end -}}
{{- end -}}
{{- end -}}

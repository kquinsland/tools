{{- $tools := site.Data.tools.tools -}}
{{- $rel := .Page.RelPermalink -}}
{{- $trimmed := strings.TrimPrefix "/tools/" $rel -}}
{{- $slug := strings.TrimSuffix "/" $trimmed -}}

{{- $tool := dict -}}
{{- range $item := $tools -}}
{{- range $key, $val := $item -}}
{{- if eq $key $slug -}}
{{- $tool = $val -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{- $deps := slice -}}
{{- with $tool.dependencies -}}
{{- $deps = . -}}
{{- end -}}

{{- if not $deps -}}
No external dependencies listed.
{{- else }}
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

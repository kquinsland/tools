{{- $tools := site.Data.tools.tools -}}
{{- $toolList := slice -}}
{{- range $item := $tools -}}
{{- range $slug, $tool := $item -}}
{{- $toolList = $toolList | append (dict
    "slug" $slug
    "title" $tool.title
    "language" ($tool.language | default "unknown")
    "dependencies" ($tool.dependencies | default (slice))
) -}}
{{- end -}}
{{- end -}}

{{- $byLanguage := dict -}}
{{- range $tool := $toolList -}}
{{- $lang := $tool.language -}}
{{- $list := index $byLanguage $lang | default (slice) -}}
{{- $list = $list | append $tool -}}
{{- $byLanguage = merge $byLanguage (dict $lang $list) -}}
{{- end -}}

{{- $languages := slice -}}
{{- range $lang, $toolsForLang := $byLanguage -}}
{{- $hasDeps := false -}}
{{- range $tool := $toolsForLang -}}
{{- if gt (len $tool.dependencies) 0 -}}
{{- $hasDeps = true -}}
{{- end -}}
{{- end -}}
{{- if $hasDeps -}}
{{- $languages = $languages | append $lang -}}
{{- end -}}
{{- end -}}
{{- $languages = sort $languages -}}

{{- range $lang := $languages -}}
{{- $toolsForLang := index $byLanguage $lang -}}
{{- $toolsForLang = sort $toolsForLang "title" }}

### {{ title $lang }}

{{- range $tool := $toolsForLang -}}
{{- $deps := $tool.dependencies -}}
{{- if gt (len $deps) 0 -}}
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
{{- end -}}

{{- $tools := site.Data.tools.tools -}}
{{- $totalTools := len $tools -}}
{{- $toolsWithDeps := 0 -}}
{{- $depCounts := dict -}}
{{- $languages := dict -}}
{{- $cdnCounts := dict -}}

{{- range $item := $tools -}}
{{- range $_, $tool := $item -}}
{{- $deps := $tool.dependencies | default (slice) -}}
{{- $language := $tool.language | default "unknown" -}}
{{- if gt (len $deps) 0 -}}
{{- $toolsWithDeps = add $toolsWithDeps 1 -}}
{{- $seen := dict -}}
{{- range $dep := $deps -}}
{{- $package := $dep.package | default "" -}}
{{- $version := $dep.version | default "" -}}
{{- $depKey := printf "%s||%s||%s" $language $package $version -}}
{{- if not (index $seen $depKey) -}}
{{- $seen = merge $seen (dict $depKey true) -}}
{{- $current := index $depCounts $depKey | default 0 -}}
{{- $depCounts = merge $depCounts (dict $depKey (add $current 1)) -}}
{{- end -}}
{{- with $dep.via -}}
{{- $host := "" -}}
{{- with (urls.Parse .) -}}
{{- if .Host -}}{{- $host = .Host -}}{{- end -}}
{{- end -}}
{{- if $host -}}
{{- $cdnCurrent := index $cdnCounts $host | default 0 -}}
{{- $cdnCounts = merge $cdnCounts (dict $host (add $cdnCurrent 1)) -}}
{{- end -}}
{{- end -}}
{{- end -}}
{{- $languages = merge $languages (dict $language true) -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{- $toolsWithoutDeps := sub $totalTools $toolsWithDeps -}}
{{- $languageList := slice -}}
{{- range $lang, $_ := $languages -}}
{{- $languageList = $languageList | append $lang -}}
{{- end -}}
{{- $languageList = sort $languageList -}}

| Total Tools | Tools Using Dependencies | Tools Without Dependencies |
| ---: | ---: | ---: |
| {{ $totalTools }} | {{ $toolsWithDeps }} | {{ $toolsWithoutDeps }} |

{{- $cdnList := slice -}}
{{- range $host, $count := $cdnCounts -}}
{{- $cdnList = $cdnList | append (dict "host" $host "count" $count) -}}
{{- end -}}
{{- $cdnList = sort $cdnList "host" -}}
{{- $cdnList = sort $cdnList "count" "desc" -}}

{{- if $cdnList }}

### CDN Hosts

| CDN Host | Use Count |
| --- | ---: |
{{- range $cdn := $cdnList }}
| {{ $cdn.host }} | {{ $cdn.count }} |
{{- end -}}
{{- end }}

{{- if not $depCounts }}
No external dependencies listed.
{{- else -}}
{{- range $lang := $languageList -}}
{{- $depList := slice -}}
{{- range $key, $count := $depCounts -}}
{{- $parts := split $key "||" -}}
{{- $keyLang := index $parts 0 -}}
{{- if eq $keyLang $lang -}}
{{- $package := index $parts 1 -}}
{{- $version := index $parts 2 -}}
{{- $depList = $depList | append (dict "package" $package "version" $version "count" $count) -}}
{{- end -}}
{{- end -}}
{{- if gt (len $depList) 0 -}}
{{- $depList = sort $depList "package" -}}
{{- $depList = sort $depList "version" -}}
{{- $depList = sort $depList "count" "desc" }}

### {{ title $lang }}

| Dependency | Version | Use Count |
| --- | --- | ---: |
{{- range $dep := $depList }}
| {{ $dep.package }} | {{ $dep.version | default "-" }} | {{ $dep.count }} |
{{- end -}}
{{- end -}}
{{- end -}}
{{- end -}}

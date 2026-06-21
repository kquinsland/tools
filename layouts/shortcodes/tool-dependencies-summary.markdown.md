{{- $stats := site.Data.tools.stats | default dict -}}
{{- $totalTools := $stats.total_tools | default 0 -}}
{{- $toolsWithDeps := $stats.tools_with_dependencies | default 0 -}}
{{- $toolsWithoutDeps := $stats.tools_without_dependencies | default 0 -}}
{{- $dependencyHosts := $stats.dependency_hosts | default (slice) -}}
{{- $dependenciesByLanguage := $stats.dependencies_by_language | default (slice) -}}

| Total Tools | Tools Using Dependencies | Tools Without Dependencies |
| ---: | ---: | ---: |
| {{ $totalTools }} | {{ $toolsWithDeps }} | {{ $toolsWithoutDeps }} |

{{- if $dependencyHosts }}

### CDN Hosts

| CDN Host | Use Count |
| --- | ---: |
{{- range $cdn := $dependencyHosts }}
| {{ $cdn.host }} | {{ $cdn.count }} |
{{- end -}}
{{- end }}

{{- if not $dependenciesByLanguage }}
No external dependencies listed.
{{- else -}}
{{- range $languageGroup := $dependenciesByLanguage -}}
{{- $deps := $languageGroup.dependencies | default (slice) -}}
{{- if gt (len $deps) 0 }}

### {{ title $languageGroup.language }}

| Dependency | Version | Use Count |
| --- | --- | ---: |
{{- range $dep := $deps }}
| {{ $dep.package }} | {{ $dep.version | default "-" }} | {{ $dep.count }} |
{{- end -}}
{{- end -}}
{{- end -}}
{{- end -}}

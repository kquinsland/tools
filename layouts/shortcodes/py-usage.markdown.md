{{- $page := .Page -}}
{{- $params := $page.Params -}}

{{- $file := "" -}}
{{- with $params.toolbox }}{{- with .file }}{{- $file = . -}}{{- end -}}{{- end -}}
{{- if not $file -}}
  {{- with $params.tool }}{{- with .file }}{{- $file = . -}}{{- end -}}{{- end -}}
{{- end -}}
{{- if not $file -}}
  {{- $file = "tool.py" -}}
{{- end -}}

{{- $base := site.BaseURL | default "/" -}}
{{- $base = strings.TrimSuffix "/" $base -}}

{{- $url := "" -}}
{{- if or (hasPrefix $file "http://") (hasPrefix $file "https://") -}}
  {{- $url = $file -}}
{{- else if hasPrefix $file "/" -}}
  {{- $url = printf "%s%s" $base $file -}}
{{- else -}}
  {{- $rel := strings.TrimSuffix "/" $page.RelPermalink -}}
  {{- $url = printf "%s%s/%s" $base $rel $file -}}
{{- end -}}
uv run "{{ $url }}"

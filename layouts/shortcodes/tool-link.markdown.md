{{- $ctx := . -}}
{{- $params := $ctx.Page.Params -}}

{{- $file := "" -}}
{{- with $params.toolbox }}{{- with .file }}{{- $file = . -}}{{- end -}}{{- end -}}
{{- if not $file -}}
  {{- with $params.tool }}{{- with .file }}{{- $file = . -}}{{- end -}}{{- end -}}
{{- end -}}
{{- if not $file -}}
  {{- $lang := lower (default "" $params.language) -}}
  {{- if eq $lang "python" -}}
    {{- $file = "tool.py" -}}
  {{- else -}}
    {{- $file = "tool.html" -}}
  {{- end -}}
{{- end -}}

{{- $href := "" -}}
{{- with $ctx.Page.Resources.GetMatch "tool-file" -}}
  {{- $href = .Permalink -}}
{{- else with $ctx.Page.Resources.GetMatch $file -}}
  {{- $href = .Permalink -}}
{{- else -}}
  {{- $base := site.BaseURL | default "/" -}}
  {{- $base = strings.TrimSuffix "/" $base -}}
  {{- if hasPrefix $file "/" -}}
    {{- $href = printf "%s%s" $base $file -}}
  {{- else -}}
    {{- $rel := strings.TrimSuffix "/" $ctx.Page.RelPermalink -}}
    {{- $href = printf "%s%s/%s" $base $rel $file -}}
  {{- end -}}
{{- end -}}

{{- $text := "" -}}
{{- if $ctx.IsNamedParams -}}
  {{- $text = $ctx.Get "link_text" -}}
{{- else if gt (len $ctx.Params) 0 -}}
  {{- $text = $ctx.Get 0 -}}
{{- end -}}

{{- if $text -}}
[{{ $text }}]({{ $href }})
{{- else -}}
{{- $href -}}
{{- end -}}

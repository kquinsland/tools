{{- $href := .Get "href" -}}
{{- $text := .InnerDeindent | strings.TrimSpace | plainify -}}
{{- if $href -}}
{{- $resourceHref := "" -}}
{{- with .Page.Resources.GetMatch $href -}}
{{- $resourceHref = .Permalink -}}
{{- end -}}
{{- if $resourceHref -}}
{{- $href = $resourceHref -}}
{{- else -}}
{{- if not (or (hasPrefix $href "http://") (hasPrefix $href "https://") (hasPrefix $href "/")) -}}
{{- $base := site.BaseURL | default "/" -}}
{{- $base = strings.TrimSuffix "/" $base -}}
{{- $rel := strings.TrimSuffix "/" $.Page.RelPermalink -}}
{{- $href = printf "%s%s/%s" $base $rel $href -}}
{{- end -}}
{{- end -}}
{{- end -}}
{{- if and $href $text -}}
[{{ $text }}]({{ $href }})
{{- else if $href -}}
{{ $href }}
{{- else -}}
{{ $text }}
{{- end -}}

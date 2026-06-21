{{- $name := "tool-icon" -}}
{{- if .IsNamedParams -}}
  {{- with .Get "name" }}{{- $name = . -}}{{- end -}}
{{- else if gt (len .Params) 0 -}}
  {{- $name = .Get 0 -}}
{{- end -}}

{{- with .Page.Resources.GetMatch $name -}}
![{{ $.Get "alt" | default "Tool icon" | plainify }}]({{ .Permalink }})
{{- end -}}

{{- define "langflow.fullname" -}}
langflow-{{ required "instanceName is required" .Values.instanceName }}
{{- end }}

{{- define "langflow.labels" -}}
app.kubernetes.io/name: langflow
app.kubernetes.io/instance: {{ include "langflow.fullname" . }}
{{- end }}

{{- define "langflow.backendSelectorLabels" -}}
app.kubernetes.io/name: langflow
app.kubernetes.io/instance: {{ include "langflow.fullname" . }}
app.kubernetes.io/component: backend
{{- end }}

{{- define "langflow.frontendSelectorLabels" -}}
app.kubernetes.io/name: langflow
app.kubernetes.io/instance: {{ include "langflow.fullname" . }}
app.kubernetes.io/component: frontend
{{- end }}

{{- define "langflow.secretName" -}}
{{- if .Values.keycloak.existingSecret -}}
{{ .Values.keycloak.existingSecret }}
{{- else -}}
{{ include "langflow.fullname" . }}-secret
{{- end }}
{{- end }}

{{- define "langflow.host" -}}
{{ include "langflow.fullname" . }}.{{ .Values.ingress.domain }}
{{- end }}

{{- define "langflow.backendImage" -}}
{{- if .Values.keycloak.enabled -}}
{{ .Values.backend.image.repository }}:{{ .Values.backend.image.ssoTag }}
{{- else -}}
{{ .Values.backend.image.repository }}:{{ .Values.backend.image.tag }}
{{- end }}
{{- end }}

{{/* SSL CA cert volume source */}}
{{- define "langflow.sslVolume" -}}
{{- if .Values.ssl.existingConfigMap -}}
configMap:
  name: {{ .Values.ssl.existingConfigMap }}
{{- else if .Values.ssl.existingSecret -}}
secret:
  secretName: {{ .Values.ssl.existingSecret }}
{{- else -}}
configMap:
  name: {{ include "langflow.fullname" . }}-ca-cert
{{- end }}
{{- end }}

{{- define "faceit.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "faceit.fullname" -}}
{{- printf "%s-%s" .Release.Name (include "faceit.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "faceit.labels" -}}
app.kubernetes.io/name: "{{ include "faceit.name" . }}"
app.kubernetes.io/instance: "{{ .Release.Name }}"
app.kubernetes.io/version: "{{ .Chart.AppVersion }}"
app.kubernetes.io/managed-by: "Helm"
{{- end -}}

{{- define "faceit.selectorLabels" -}}
app.kubernetes.io/name: "{{ include "faceit.name" . }}"
app.kubernetes.io/instance: "{{ .Release.Name }}"
{{- end -}}

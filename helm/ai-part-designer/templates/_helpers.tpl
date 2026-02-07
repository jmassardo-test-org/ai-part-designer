{{/*
Generate full resource name with release
*/}}
{{- define "ai-part-designer.fullname" -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Common labels for all resources
*/}}
{{- define "ai-part-designer.labels" -}}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: ai-part-designer
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end -}}

{{/*
Backend selector labels
*/}}
{{- define "ai-part-designer.backend.selectorLabels" -}}
app.kubernetes.io/name: backend
app.kubernetes.io/component: api
{{- end -}}

{{/*
Frontend selector labels
*/}}
{{- define "ai-part-designer.frontend.selectorLabels" -}}
app.kubernetes.io/name: frontend
app.kubernetes.io/component: web
{{- end -}}

{{/*
Celery worker selector labels
*/}}
{{- define "ai-part-designer.worker.selectorLabels" -}}
app.kubernetes.io/name: celery-worker
app.kubernetes.io/component: worker
{{- end -}}

{{/*
Celery beat selector labels
*/}}
{{- define "ai-part-designer.beat.selectorLabels" -}}
app.kubernetes.io/name: celery-beat
app.kubernetes.io/component: scheduler
{{- end -}}

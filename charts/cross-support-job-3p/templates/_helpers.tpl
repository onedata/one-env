{{/* vim: set filetype=mustache: */}}

{{- define "json_quoted_list" -}}
  {{- if kindIs "slice" .list -}}
   {{- printf "-d \"'{ \\\"%s\\\": [ " .name -}}
   {{- range (initial .list) -}}
    {{- printf "\\\"%s\\\", " . -}}
   {{- end -}}
   {{- if .list -}}
    {{- printf "\\\"%s\\\" " (last .list) -}}
   {{- end -}}
   {{- printf "]}'\" " -}}
  {{- end -}}
{{- end -}}

{{- define "providerName" -}}
  {{- printf "%s-%s" "oneprovider" . | trimSuffix "-" -}}
{{- end -}}

{{- define "admin_username_template" -}}
{{- if hasKey (index .Values "onedata-3p" "onezone") "onezoneAdmin" -}}
{{- (index .Values "onedata-3p" "onezone" "onezoneAdmin" "name") }}
{{- else -}}
{{- printf "%s" "UNINITIALIZED" }}
{{- end -}}
{{- end -}}

{{- define "admin_password_template" -}}
{{- if hasKey (index .Values "onedata-3p" "onezone") "onezoneAdmin" -}}
{{- (index .Values "onedata-3p" "onezone" "onezoneAdmin" "password") }}
{{- else -}}
{{- printf "%s" "UNINITIALIZED" }}
{{- end -}}
{{- end -}}

{{- define "keycloak_realmId_template" -}}
{{- if hasKey (index .Values "keycloakInstance" ) "init" }}
{{- .Values.keycloakInstance.init.realmId -}}
{{- else -}}
{{- printf "%s" "UNINITIALIZED" }}
{{- end -}}
{{- end -}}

{{- define "keycloak_adminUsername_template" -}}
{{- if hasKey (index .Values "keycloakInstance" ) "init" }}
{{- .Values.keycloakInstance.init.adminUsername -}}
{{- else -}}
{{- printf "%s" "UNINITIALIZED" }}
{{- end -}}
{{- end -}}

{{- define "keycloak_adminPassword_template" -}}
{{- if hasKey (index .Values "keycloakInstance" ) "init" }}
{{- .Values.keycloakInstance.init.adminPassword -}}
{{- else -}}
{{- printf "%s" "UNINITIALIZED" }}
{{- end -}}
{{- end -}}

{{- define "keycloak_idpName_template" -}}
{{- if hasKey (index .Values "keycloakInstance" ) "idpName" }}
{{- .Values.keycloakInstance.idpName -}}
{{- else -}}
{{- printf "%s" "UNINITIALIZED" }}
{{- end -}}
{{- end -}}

{{- define "keycloak_tokenPrefix_template" -}}
{{- if hasKey (index .Values "keycloakInstance" ) "tokenPrefix" }}
{{- .Values.keycloakInstance.tokenPrefix -}}
{{- else -}}
{{- printf "%s" "UNINITIALIZED" }}
{{- end -}}
{{- end -}}

---
type: Deployment
title: Despliegue y variables de entorno
description: Cómo se construye y corre el servicio, y qué variables de entorno lee cada módulo.
resource: https://github.com/pa70xd/e2c/blob/claude/admiring-lovelace-3oh7g0/Dockerfile
tags: [docker, cloud-run, env]
---

# Build y ejecución

* Imagen base `python:3.14` sin fijar parche.
* `pip install -r requirements.txt` con 88 paquetes fijados. Sin uso directo: `pg8000`, `SQLAlchemy`, `cloud-sql-python-connector`, `google-cloud-pubsub`. `dotenv==0.9.9` y `python-dotenv==1.2.2` duplican función.
* Comando: `uvicorn main:app --host 0.0.0.0 --port 8080`.
* Despliegue en Cloud Run (`.gcloudignore` presente).

# Variables de entorno

| Variable | Quién la lee | Uso |
|---|---|---|
| `CLIENT_ID`, `CLIENT_SECRET`, `TENANT_ID` | handler, subscriptions, graphapi | MSAL y Graph |
| `DEBUG` | service, email_type, repository | Modo depuración. Escribe `email.json`. **Si no está definida, el código apunta a las tablas de PRODUCCIÓN**: `repository/*/consultas_postgre.py:11-16` compara `DEBUG` con `"true"` y, si no, usa producción (el import imprime `[BASEDATOS] dirigido a -> PRODUCCIÓN`). Para usar las tablas `*_qa` hay que definir `DEBUG=true`. |
| `MAPS_KEY` | process_data, geocoding | Google Geocoding |
| `SECRET_PG_ACC` | postgres | Nombre del secreto de PostgreSQL |
| `DB_HOST`, `DB_NAME`, `DB_PORT` | postgres | Conexión |
| `PROJECT_ID` | excel_ingestion, tableau | GCP |
| `REPARE_BUCKET` | excel_ingestion | Bucket (subida comentada) |
| `TOKEN_NAME`, `TOKEN_SECRET` | tableau | Login VizQL |
| `FILE_ID`, `DRIVE_ID` | graphapi (getTemplate) | Sin uso activo |
| `CORS_ALLOW_ORIGINS` | main | Opcional. Mergeado en `claude/admiring-lovelace-3oh7g0` (rama `claude/e2c-fix-orquestador`). Orígenes separados por comas. Sin ella: `"*"` sin credenciales. |
| `GRAPH_CLIENT_STATE` | handler | Opcional. Mergeado en `claude/admiring-lovelace-3oh7g0` (rama `claude/e2c-fix-orquestador`). Debe coincidir con el `clientState` de la suscripción; `subscriptions.py` aún no lo envía. |
| `CLASSIFIER_GATE` | classifier (Fase 3) | Opcional. Proveedor del gate; default `regex`. Verificado en `classifier/registry.py` de la rama `claude/e2c-classifier-core` (`926d693`, sin mergear). |
| `CLASSIFIER_EXTRACT` | classifier (Fase 3) | Opcional. Proveedor de la extracción; default `regex`. Misma rama. |
| `CLASSIFIER_MIN_CONFIDENCE` | classifier (Fase 3) | Opcional. Confianza mínima del gate externo; default 0.7. Misma rama. |
| `ANTHROPIC_API_KEY` | provider-haiku (Fase 3) | Opcional. Reportada por la orquestadora; no la he visto en el código (rama `claude/e2c-provider-haiku`, sin verificar). No pegues su valor en el repo. |

Sin uso: `MAIL`, `NOTIFICATIONS_TOPIC_ID`, `NOTIFY_ERROR_MAILS`, `SECRET_ID`, `GOOGLE_MAPS_API_KEY` (catálogos muertos).

Para pruebas, ver el [runbook del lunes](runbook-lunes.md).

# Problemas

* Dockerfile corre como root.
* Sin `.dockerignore`: la imagen incluye `.git` y datos reales.

Ver [seguridad](../riesgos/seguridad.md).

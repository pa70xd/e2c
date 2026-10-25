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
| `DEBUG` | service, email_type | Modo depuración. Escribe `email.json`. |
| `MAPS_KEY` | process_data, geocoding | Google Geocoding |
| `SECRET_PG_ACC` | postgres | Nombre del secreto de PostgreSQL |
| `DB_HOST`, `DB_NAME`, `DB_PORT` | postgres | Conexión |
| `PROJECT_ID` | excel_ingestion, tableau | GCP |
| `REPARE_BUCKET` | excel_ingestion | Bucket (subida comentada) |
| `TOKEN_NAME`, `TOKEN_SECRET` | tableau | Login VizQL |
| `FILE_ID`, `DRIVE_ID` | graphapi (getTemplate) | Sin uso activo |
| `CORS_ALLOW_ORIGINS` | main | Opcional, solo en rama `claude/e2c-fix-orquestador` (sin mergear). Orígenes separados por comas. Sin ella: `"*"` sin credenciales. |
| `GRAPH_CLIENT_STATE` | handler | Opcional, solo en rama `claude/e2c-fix-orquestador` (sin mergear). Debe coincidir con el `clientState` de la suscripción; `subscriptions.py` aún no lo envía. |

Sin uso: `MAIL`, `NOTIFICATIONS_TOPIC_ID`, `NOTIFY_ERROR_MAILS`, `SECRET_ID`, `GOOGLE_MAPS_API_KEY` (catálogos muertos).

# Problemas

* Dockerfile corre como root.
* Sin `.dockerignore`: la imagen incluye `.git` y datos reales.

Ver [seguridad](../riesgos/seguridad.md).

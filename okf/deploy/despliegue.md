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
| `CLASSIFIER_GATE` | classifier (Fase 3) | Opcional. Proveedor del gate; default `regex`. Verificado en `classifier/registry.py`, mergeado en la base. |
| `CLASSIFIER_EXTRACT` | classifier (Fase 3) | Opcional. Proveedor de la extracción; default `regex`. Misma rama. |
| `CLASSIFIER_MIN_CONFIDENCE` | classifier (Fase 3) | Opcional. Confianza mínima del gate externo; default 0.7. Misma rama. |
| `ANTHROPIC_API_KEY` | provider-haiku (Fase 3) | Opcional. Verificada en `classifier/providers/haiku.py`, mergeado en la base. Sin ella, el proveedor haiku cae a regex. No pegues su valor en el repo. |
| `E2C_ANTHROPIC_API_KEY` | eval / entornos cloud | Solo en entornos cloud donde la plataforma descarta `ANTHROPIC_*`: guarda la key de la organización con este nombre y pásala como `ANTHROPIC_API_KEY` al comando. Según la orquestadora; no verificada en código. No pegues el valor en el repo. |
| `CLASSIFIER_PROMPT_VERSION` | classifier / haiku (Fase 3) | Opcional. Vacía o `v1` = prompts actuales; `v2` = con contexto de negocio. Rama `claude/e2c-prompt-v2`, sin mergear. |
| `E2C_TEST_MAILBOX` | email_type, service | Opcional. Dirección del buzón de pruebas, mapeada al cliente `test`; sin ella (o vacía) no hay buzón de pruebas. Rama `claude/e2c-fix-holanda-indice` (sin mergear); verificada en `src/email_type.py`. No pegues la dirección en el repo. Ojo: la misma dirección aparece como remitente hardcodeado (`EMAIL_SENDER`) y como default de `MAIL`; ver [graph-api](../infrastructure/graph-api.md). |
| `CLASSIFIER_SHADOW`, `CLASSIFIER_SHADOW_SAMPLE` | classifier (Fase 3) | Opcionales. Proveedor del gate en sombra (vacía = apagado) y fracción de correos (0.0-1.0, default 1.0). Rama `claude/e2c-sombra`, sin mergear. **Bloqueado con correos reales hasta `redact-v2`.** Ver [sombra](../classifier/sombra.md). |
| `E2C_CLIENTES_HABILITADOS` | service (Fase 4) | Opcional. Lista de clientes habilitados. Sin ella solo corren los 4 clientes actuales (danone, holanda, penafiel/kdrp, heineken/hnk). Rama `claude/e2c-lector-excel`; según la orquestadora, aún no verificada en código. Oxxo queda apagado por defecto. |
| `EVAL_PRICE_IN`, `EVAL_PRICE_OUT` | eval (Fase 3) | Opcionales. USD por millón de tokens para calcular el costo de haiku en el evaluador. Mergeado en la base. |

Sin uso: `MAIL`, `NOTIFICATIONS_TOPIC_ID`, `NOTIFY_ERROR_MAILS`, `SECRET_ID`, `GOOGLE_MAPS_API_KEY` (catálogos muertos).

Para pruebas, ver el [runbook del lunes](runbook-lunes.md).

# Problemas

* Dockerfile corre como root.
* Sin `.dockerignore`: la imagen incluye `.git` y datos reales.

Ver [seguridad](../riesgos/seguridad.md).

---
type: Module
title: handler y main
description: App FastAPI y router con los endpoints de Graph (validación, recepción y renovación de suscripciones).
resource: https://github.com/pa70xd/e2c/blob/claude/admiring-lovelace-3oh7g0/src/handler.py
tags: [fastapi, endpoints]
---

# main.py

* `app = FastAPI(version="0.33")`.
* CORS: `allow_origins=["*"]` con `allow_credentials=True` (en rama `claude/e2c-fix-orquestador`, sin mergear: configurable con `CORS_ALLOW_ORIGINS`, sin credenciales por defecto). Ver [seguridad](../riesgos/seguridad.md).
* Monta el router de `src/handler.py`.

# Endpoints

| Método y ruta | Qué hace |
|---|---|
| `POST /lifecyclenotif` | Responde `validationToken`. Ante `reauthorizationRequired`, renueva la suscripción. |
| `POST /receive_mail` | Responde `validationToken`. Encola cada mensaje en `BackgroundTasks` con `processMail`. |

# Variables que lee

* `CLIENT_ID`, `CLIENT_SECRET`, `TENANT_ID`: usadas para MSAL y la renovación.
* `MAIL`, `PROJECT_ID`, `NOTIFICATIONS_TOPIC_ID`: definidas pero no usadas.

# Problemas

* No valida `clientState` en `/receive_mail`. En rama `claude/e2c-fix-orquestador` (sin mergear) lo valida si `GRAPH_CLIENT_STATE` está definida; `/lifecyclenotif` sigue sin validar. Ver [seguridad](../riesgos/seguridad.md).
* `ReuthorizeWebhook` llama a MSAL de forma síncrona dentro de un handler async.
* Imports duplicados y `pubsub_v1` importado sin uso: no hay Pub/Sub en el flujo.

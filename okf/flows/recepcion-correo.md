---
type: Process Flow
title: Recepción de correo
description: Cómo entra un correo desde Microsoft Graph hasta el procesamiento en background.
resource: https://github.com/pa70xd/e2c/blob/claude/admiring-lovelace-3oh7g0/src/handler.py
tags: [flujo, graph, webhook]
---

# Pasos

1. Graph hace `POST /receive_mail` con un payload `value` de mensajes. Ver [handler](../services/handler.md).
2. Si el request trae `validationToken`, se responde el token (handshake de suscripción).
3. Por cada mensaje se encola `procesar_mail_background` con `BackgroundTasks`. La respuesta HTTP es inmediata.
4. `processMail` ([service](../services/service.md)) hace GET del mensaje completo en Graph.
5. `EMAIL_TYPE.validate_email` descarta borradores, respuestas automáticas, correos vacíos y duplicados (ventana de 120 s en memoria). Ver [email_type](../services/email-type.md).
6. `detect_customer` busca el buzón del cliente en To, CC y From usando `config/email_index.json`.
7. Según el cliente y la dirección del correo se elige un parser de la mesa `PARSERS_INIT` o `PARSERS_REPLY`.

# Ramas de salida

* Correo ignorado: borrador, automático, vacío o duplicado.
* Cliente no reconocido: se termina sin respuesta.
* Excepción en background: se registra en logs; no hay reintento ni notificación.

# Riesgos del punto de entrada

* `/receive_mail` no valida `clientState`. Cualquier POST con un id de mensaje real dispara el procesamiento. Ver [bugs](../riesgos/bugs.md) y [seguridad](../riesgos/seguridad.md).
* `/lifecyclenotif` renueva la suscripción con PATCH +2 días, con token obtenido de forma síncrona dentro de un handler async.

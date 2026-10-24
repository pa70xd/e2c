---
type: Integration
title: Microsoft Graph
description: Lectura de correos, borradores y respuestas, y suscripciones de Graph.
resource: https://github.com/pa70xd/e2c/blob/claude/admiring-lovelace-3oh7g0/infrastructure/graphapi/graphapi.py
tags: [graph, microsoft, correo]
---

# Uso activo

* `getClient` y `getToken` (MSAL, client credentials).
* `reply_mail_onl_text`: respuesta de texto.
* `reply_mail_init_files`: crea borrador de respuesta con adjuntos y lo envía.
* Lectura del mensaje completo con `Prefer: outlook.body-content-type="text"`.

# Sin uso

`getTemplate` (usa `FILE_ID` y `DRIVE_ID`), `send_mail_file`, `sendMail`.

# Variables

* `CLIENT_ID`, `CLIENT_SECRET`, `TENANT_ID`.
* `SECRET_ID`, `NOTIFY_ERROR_MAILS`: sin uso.

# Problemas

* Remitente hardcodeado `solkos@imberacooling.com`, ignora la variable `MAIL`.
* Fuerza content-type xlsx en todos los adjuntos.
* Un token obtenido sin uso en `getTemplate`.

Ver [suscripciones](subscriptions.md) y [recepción de correo](../flows/recepcion-correo.md).

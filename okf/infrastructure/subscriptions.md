---
type: Script
title: Suscripciones Graph (script manual)
description: Script para crear, listar y borrar suscripciones de Graph sobre los buzones de cliente. No se importa desde la app.
resource: https://github.com/pa70xd/e2c/blob/claude/admiring-lovelace-3oh7g0/subscriptions.py
tags: [graph, suscripciones, script]
---

# Qué hace

* `test`: crea suscripción sobre `users/{email}/messages`. La dirección de prueba sigue hardcodeada en `subscriptions.py`, aunque en la rama `claude/e2c-fix-holanda-indice` (sin mergear) ya sale de `email_index.json` y se toma de `E2C_TEST_MAILBOX` (según la sesión; pendiente).
* `list_subscriptions`, `delete_subscription`, `delete_all_subscriptions`.
* Buzones activos: danone, holanda, kdrp. Heineken, KOF, Imbera y Torrey comentados.

# Variables

* `CLIENT_ID`, `CLIENT_SECRET`, `TENANT_ID`.

# Problemas

* Si el token falla, envía `Bearer None`.
* El cuerpo de la suscripción se sobrescribe antes de usarse. Cinco días probablemente excede el máximo que acepta Graph.
* `datetime.now()` local con sufijo `Z`.
* Usa `requests` síncrono dentro de función async.
* Si Graph devuelve lista vacía, no crea ninguna suscripción.
* Dos URLs de Cloud Run distintas en el mismo archivo.

Ver [Graph](graph-api.md).

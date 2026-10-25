---
type: Process Flow
title: Respuesta, outbound y comandos del bot
description: Cómo se resuelve un correo que responde a una solicitud, incluido el outbound de REPARE y los comandos bot.*.
resource: https://github.com/pa70xd/e2c/blob/claude/admiring-lovelace-3oh7g0/parsers/danone.py
tags: [flujo, hilo, outbound, bot]
---

# Dirección del correo

Según `EMAIL_TYPE.detect_direccion` ([email_type](../services/email-type.md)):

* **inbound**: cliente → REPARE. Trae Excel con datos o actualizaciones.
* **outbound**: REPARE → cliente. Trae Excel con OS o estatus.
* **reply_to_bot**: REPARE → REPARE. Comandos `bot.*`.
* **bot**: REPARE → REPARE con la frase de plantilla del bot.

# Vinculación con la solicitud

* Danone y Penafiel: `email_reply_validate(conversation_id, subject)`. El asunto solo desempata. No filtra por estado.
* Holanda: no usa hilo. Resuelve por folio `REPARE_\d+`, primero en texto nuevo y luego en el cuerpo completo.
* Heineken: el hilo solo se usa en D2D. En RUTA se resuelve por folio.

# Inbound (cliente → REPARE)

* Requiere Excel. Sin Excel no se procesa.
* Aplica las mismas reglas de negocio que la solicitud inicial, luego `insert_update_cooler` y `update_email_request`. En la base (rama `claude/e2c-fix-returning`), una fila ACCEPTED reenviada no se aplica y se loguea para revisión.
* Responde con `msj_add_cliente`.

# Outbound (REPARE → cliente)

* Concilia las OS fila a fila: D2D por serie, RUTA por orden o folio.
* Calcula estatus con reglas por cliente. Heineken y Penafiel usan prefijo 403; Holanda cuenta todas las OS como "con OS" (diferencia reportada).
* Responde con `msj_solicitud_completa_esc1` si el estatus es COMPLETED, o `msj_cambios` si no.

# Comandos bot

Palabras reservadas en `config/config_general/palabras_reser.py`. Se buscan como subcadena en minúsculas.

| Comando | Danone / Penafiel | Heineken | Holanda |
|---|---|---|---|
| `bot.help`, `bot.ayuda` | respuesta de ayuda | ayuda | ayuda |
| `bot.estatus`, `bot.status` | contadores y tickets | estatus por código | estatus por folio |
| `bot.cancelar` | cancela solicitud; **no cancela coolers pendientes** | cancela pendientes y solicitud | cancela pendientes y solicitud |
| `bot.finalizar`, `bot.cerrar` | completa solicitud | completa solicitud | completa solicitud |
| `bot.global` | lista global (solo Danone) | estado global | estado global |

Un comando desconocido responde `msj_comando_no_reconocido`.

# Riesgos

* Danone `bot.cancelar` no cancela coolers. Un outbound posterior reabre la solicitud, porque `email_request_update.sql` no excluye CANCELLED. Corregido mergeado en `claude/admiring-lovelace-3oh7g0` (rama `claude/e2c-fix-parsers`); Penafiel también (commit `a5bd0fc`). Ver [bugs](../riesgos/bugs.md).
* `bot.estatus` de Danone puede lanzar `UnboundLocalError` si la consulta falla.
* Los comandos responden éxito aunque el UPDATE no haya afectado filas.

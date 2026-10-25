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
| `bot.cancelar` | cancela pendientes y solicitud (en la base desde fix-parsers; antes no cancelaba coolers) | cancela pendientes y solicitud | cancela pendientes y solicitud |
| `bot.finalizar`, `bot.cerrar` | completa solicitud | completa solicitud | completa solicitud |
| `bot.global` | lista global (`get_email_request_global`) | estado global | estado global |

Un comando desconocido responde `msj_comando_no_reconocido`, pero hoy es inalcanzable: el lector solo detecta `palabras_reservadas`, así que un `bot.*` desconocido no se detecta ni se responde.

# Despachador único (rama `claude/e2c-bot-commands`, Fase 2, sin mergear)

Verificado en la rama: existen `bot/commands.py`, `bot/perfiles.py` y `tests/unit_bot/`. Los parsers de Danone, Penafiel, Holanda y Heineken delegan en `ejecutar(perfil, result_type, resolver)`; `parse()`, los `*_REPLY` y la interfaz de `DB_POSTGRE` quedan iguales. Según la sesión, el comportamiento no cambió (matriz antes/después); yo verifiqué que la suite pasa con los goldens sin tocar (no regeneré goldens).

Flujo común: sin palabra → `None`; `help`/`ayuda` → `msj_ayuda`; `global` → datos + Excel; otra palabra → `msj_comando_no_reconocido`; luego se resuelve la solicitud y se atiende `estatus`, `cancelar` o `finalizar`.

* **Resolver la solicitud**: Danone y Penafiel por hilo (`email_reply_validate`, fuera del bot). Holanda siempre por folio (`DB_HOLANDA.get_request`). Heineken: D2D por hilo; sin `request_code`, por folio (`DB_HEINEKEN.get_request`). Sin folio → `msj_folio_requerido()`; folio inexistente → `msj_folio_requerido(folio)`.
* **Lectura de `result_type`**: Danone y Penafiel indexan directo (`KeyError` si falta la llave); Holanda y Heineken usan `.get()`.
* **`global`**: si hay datos, `process_email_request_global` y luego `msj_global`; con error o datos vacíos responde sin adjunto.
* **`estatus`**: Danone y Penafiel vacío o error → `msj_fail()`; Holanda → `msj_folio_requerido(folio)`; Heineken → `msj_folio_requerido(request_code)`.
* **`cancelar`**: `cancel_pending_coolers`, luego `cancel_email_request`, luego `msj_cancelar`. Si el primero falla, el segundo no corre y **se responde éxito igual**.
* **`finalizar`/`cerrar`**: `complete_email_request` y `msj_finalizar`; si falla, responde éxito igual.
* **Logs**: Danone y Penafiel conservan "No se logro cancelar la solicitud {e}" también en `estatus` (copy-paste). Holanda y Heineken: `[CLIENTE][BOT][ERROR] No se logró consultar el estatus de / cancelar / finalizar {rc}: {e}`.

Cuando la rama se mergee, el cambio debe quedar como refactor sin cambio de comportamiento.

# Riesgos

* Danone `bot.cancelar` no cancela coolers. Un outbound posterior reabre la solicitud, porque `email_request_update.sql` no excluye CANCELLED. Corregido mergeado en `claude/admiring-lovelace-3oh7g0` (rama `claude/e2c-fix-parsers`); Penafiel también (commit `a5bd0fc`). Ver [bugs](../riesgos/bugs.md).
* `bot.estatus` de Danone podía lanzar `UnboundLocalError`: corregido en la base (`2ab001b`).
* Los comandos responden éxito aunque el UPDATE no haya afectado filas.

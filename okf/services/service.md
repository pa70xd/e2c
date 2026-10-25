---
type: Module
title: service (orquestador)
description: processMail, el orquestador que conecta Graph, la clasificación de correos, los parsers y la respuesta.
resource: https://github.com/pa70xd/e2c/blob/claude/admiring-lovelace-3oh7g0/src/service.py
tags: [orquestador, processMail]
---

# processMail

1. GET del mensaje completo en Graph.
2. `EMAIL_TYPE.validate_email`.
3. `detect_customer` y, si es `test`, `resolve_test_customer` por asunto.
4. Rama reply si el correo está en un hilo ya conocido (`db.conversation_exists`), salvo en DEBUG.
5. Rama init en otro caso.
6. Respuesta por Graph con `reply_mail_onl_text` o `reply_mail_init_files`.
7. Cierre de DuckDB en cada salida.

# Mapas

* `PARSERS_INIT` y `PARSERS_REPLY`: `danone`, `penafiel`, `holanda`, `heineken` y las variantes `test_*`.
* KOF no está registrado.
* `CUSTOMER_INDEX` se carga de `config/email_index.json` con ruta relativa al directorio de trabajo.

# Problemas

* `validator.detect_direccion(email)` puede devolver `None`. Desempaquetarlo en la línea 245 revienta con `TypeError` sin capturar. Verificado. Corregido mergeado en `claude/admiring-lovelace-3oh7g0` (rama `claude/e2c-fix-orquestador`).
* `PARSERS_REPLY[customer]` lanza `KeyError` fuera del try.
* En DEBUG escribe `email.json` con el correo completo. Ver [seguridad](../riesgos/seguridad.md).
* Varias salidas tempranas no cierran DuckDB.
* `flujo` y `sendMail` no se usan. Imports duplicados.

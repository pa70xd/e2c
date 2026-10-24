---
type: Client Integration
title: KOF (stub, no soportado)
description: KOF no está soportado de extremo a extremo. Existe un stub y un archivo de configuración vacío.
resource: https://github.com/pa70xd/e2c/blob/claude/admiring-lovelace-3oh7g0/parsers/kof.py
tags: [kof, pendiente]
---

# Estado

* `parsers/kof.py`: stub que solo imprime. No está registrado en `PARSERS_INIT` ni `PARSERS_REPLY`.
* `config/customers/kof/customer.json`: archivo de 0 bytes.
* `config/email_index.json` no mapea el buzón de KOF.
* `subscriptions.py` tiene la suscripción de KOF comentada.

# Para habilitarlo se necesita

* Reglas de negocio y columnas de KOF.
* Buzón en `email_index.json` y suscripción activa.
* Registro en `PARSERS_INIT` y `PARSERS_REPLY`.
* Ver [índice de clientes](../clients/index.md).

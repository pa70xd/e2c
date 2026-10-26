---
type: Client Integration
title: Torrey
description: Parser de Torrey (máquinas de hielo), mergeado en la base y apagado por defecto (E2C_CLIENTES_HABILITADOS).
tags: [parsers, torrey, fase-4]
---

# Estado

Mergeado en la base (`594ca0d`, rama `claude/e2c-imbera-torrey`). **Apagado por defecto**: se enciende con `torrey` en `E2C_CLIENTES_HABILITADOS`. Comparte flujo con Imbera: ver [Imbera y Torrey](imbera-torrey.md) (`parsers/torrey_parse/hielo.py`).

# Lo esencial

* La máquina de hielo queda con `cooler_request.cliente = IMBERA` dentro del `email_request` de Torrey y se contesta en el hilo de Torrey.
* Torrey se marca siempre como garantía; si falta la factura PDF, solo se avisa en la respuesta.
* Preguntas de negocio sin responder: ver [preguntas abiertas](../riesgos/preguntas-abiertas.md) (factura obligatoria, `email_request` aparte, catálogo de modelos de hielo).

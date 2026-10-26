---
type: Client Integration
title: Imbera
description: Parser de Imbera ("Lay Out Repare"), multi-cliente, mergeado en la base y apagado por defecto (E2C_CLIENTES_HABILITADOS).
tags: [parsers, imbera, fase-4]
---

# Estado

Mergeado en la base (`594ca0d`, rama `claude/e2c-imbera-torrey`). **Apagado por defecto**: se enciende con `imbera` en `E2C_CLIENTES_HABILITADOS` ([despliegue](../deploy/despliegue.md)). Detalle de lectura, reglas, rechazos y conciliación en [Imbera y Torrey](imbera-torrey.md), que cubre los dos clientes porque comparten flujo (`parsers/imbera_parse/`).

# Lo esencial

* Imbera es multi-cliente: el sub-cliente se lee del asunto o del cuerpo y va a `cooler_request.cbu` (solo JUMEX, PISA y ELECTROLIT reconocidos).
* Folios `IMB-`/`REP-` a `folio`; la OS de una garantía a `ticket_solicitud`.
* La garantía solo se **marca**; la valida la etapa 2.
* Preguntas de negocio sin responder: ver [preguntas abiertas](../riesgos/preguntas-abiertas.md) (sub-cliente, criterio de garantía, institucionales, formato de OS, seguimientos sin Excel).

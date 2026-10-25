---
type: Database Schema
title: Modelo de datos inferido
description: Tablas, columnas clave, estados y transiciones. No hay DDL en el repo; el esquema se infiere por uso.
resource: https://github.com/pa70xd/e2c/blob/claude/admiring-lovelace-3oh7g0/repository/querys/genericas/
tags: [postgres, esquema, estados]
---

# Tablas (esquema `repare_email_parse`)

| Tabla | Rol | Columnas clave |
|---|---|---|
| `emails_log` | Un registro por correo procesado | `graph_message_id` (único), `request_code`, `conversation_id`, `customer`, `link_email` |
| `email_request` | Cabecera de solicitud | `request_code` (único), `customer`, `status`, `total_coolers`, `pending_coolers`, `completed_coolers`, `failed_coolers`, `priority` |
| `cooler_request` | Una fila por equipo o caso | `request_code`, `row_number`, `serie_fabricante`, `serie_dnn_bnf`, `modelo`, `os`, `status`, `rejection_reason`, `folio`, `ticket_solicitud`, `prioridad`, `cp`, `lat`/`long` |
| `solicitud_rechazadas` | Filas rechazadas por reglas | `MOTIVO`, `TABLA_ORIGEN`, `HASH_ORIGINAL`, `FILA_ORIGINAL` (varía por cliente) |
| `catalogo_servicios_ruta`, `cp_mov`, `cp_ruta`, `distribuidoras_repare` | Catálogos de distribuidora | Lookup por CP |

# Columnas reutilizadas por cliente

* `folio`: CASO2 en Holanda, ORDEN en Heineken RUTA.
* `serie_dnn_bnf`: Congelador en Holanda, ACTIVO en Heineken D2D.
* `tipo_servicio`: FALLA en Heineken D2D.
* `cbu`: Origen en Holanda.
* `ticket_solicitud`: TE en Holanda.

# Estados

`email_request.status`: IN_PROGRESS (inicial), COMPLETED, CANCELLED. PENDING aparece solo en mensajes.

`cooler_request.status`: PENDING (inicial), ACCEPTED, CANCELLED. REJECTED lo escriben parsers de Danone pero ningún SQL lo cuenta.

Prioridad: HIGH en Danone; MEDIUM en Heineken y Holanda (SQL dice MEDIA).

# Transiciones

* Outbound: cooler → ACCEPTED, PENDING o REJECTED; luego `update_email_request` recalcula.
* `bot.cancelar`: request → CANCELLED. Heineken y Holanda también pasan coolers PENDING → CANCELLED. Danone y Penafiel no (corregido mergeado en `claude/admiring-lovelace-3oh7g0` (rama `claude/e2c-fix-parsers`).
* `bot.finalizar`: request → COMPLETED desde cualquier estado, incluido CANCELLED. Ver [bugs](../riesgos/bugs.md).
* Un outbound posterior puede revivir un CANCELLED en Danone.

# Riesgos de integridad

* Sin índices únicos verificables en el repo: los `WHERE NOT EXISTS` pueden duplicar con concurrencia.
* `update_cooler.sql` no filtra por `row_number`. Si la serie es vacía, puede actualizar varias filas.

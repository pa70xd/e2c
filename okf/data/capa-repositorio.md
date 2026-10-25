---
type: Module
title: Capa de repositorio
description: Funciones de acceso a PostgreSQL por cliente, SQL asociado y patrón de conexión.
resource: https://github.com/pa70xd/e2c/blob/claude/admiring-lovelace-3oh7g0/repository/
tags: [postgres, sql, repositorio]
---

# Patrón de conexión

* `infrastructure/database/postgres.py`: `get_connection` lee el secreto de Secret Manager en cada llamada y conecta con psycopg2 y `RealDictCursor`.
* `execute_query`: una conexión por statement, commit y cierre. Rollback solo ante excepción.
* Sin pool. Sin transacciones explícitas en `repository/`.
* El SQL se lee de archivo en cada llamada. Sin caché.
* Esquema fijo `repare_email_parse`. Algunos SQL usan `repare.` literal.

# Módulos

| Módulo | Qué es |
|---|---|
| `repository/danone/consultas_postgre.py` (`DB_POSTGRE`) | Base genérica. Gen, Penafiel y Danone tienen la misma clase. |
| `repository/penafiel/`, `repository/gen/` | Copias casi idénticas de la base. |
| `repository/heineken/` (`DB_HEINEKEN`) | Conciliación D2D y ruta, series abiertas, serie genérica. |
| `repository/holanda/` (`DB_HOLANDA`) | Inserción por CASO2, actualización de OS por CASO2. |
| `repository/querys/genericas/` | SQL genérico compartido. |

# Funciones clave

* `save_email_log_init`: insert en `emails_log` con `ON CONFLICT (graph_message_id)`.
* `send_email_request`: insert en `email_request`.
* `send_email_coolers`: insert en `cooler_request` con `WHERE NOT EXISTS`.
* `insert_update_cooler`: update de la fila PENDING y luego insert. Ver [bugs](../riesgos/bugs.md).
* `update_cooler`: update por request y serie.
* `update_email_request`: recalcula contadores y status.
* `send_email_coolers` (danone, gen, penafiel): mergeado en `claude/admiring-lovelace-3oh7g0` (rama `claude/e2c-fix-parsers`) usa las series limpias (NaN→None) en INSERT y `WHERE NOT EXISTS`.
* `cancel_email_request`, `complete_email_request`, `cancel_pending_coolers`.
* `get_distribuidora_mov` y `get_distribuidora_ruta`: lookup por CP y precio.

# Riesgos

* Interpolación de nombres de tabla y de constantes con `.format()`. No hay entrada de usuario sin escapar, pero hay `'{cliente}'` dentro de comillas en SQL de Heineken y Holanda.
* Varias operaciones multi-paso sin transacción. Ver [flujo solicitud inicial](../flows/solicitud-inicial.md).
* Sin protección de concurrencia en `MAX(row_number)` de Heineken.
* Comandos responden éxito aunque el UPDATE no afecte filas.

Ver modelo en [modelo de datos](modelo-datos.md) y bugs en [bugs](../riesgos/bugs.md).

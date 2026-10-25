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
| `repository/danone/consultas_postgre.py` (`DB_POSTGRE`) | En la base de integración: base genérica; Gen, Penafiel y Danone tienen la misma clase. En la rama `claude/e2c-core-repository` solo contiene los overrides sobre `DBPostgreBase` (ver abajo). |
| `repository/penafiel/`, `repository/gen/` | En la base de integración, copias casi idénticas. En la rama, subclases con solo los overrides. |
| `repository/heineken/` (`DB_HEINEKEN`) | Conciliación D2D y ruta, series abiertas, serie genérica. |
| `repository/holanda/` (`DB_HOLANDA`) | Inserción por CASO2, actualización de OS por CASO2. |
| `repository/querys/genericas/` | SQL genérico compartido. |

# Base común (rama `%s`, Fase 2, sin mergear)

Commits `351ee40` y `ecaae40`. Verificado en la rama: existe `repository/core/consultas_postgre.py` (752 líneas) con `DBPostgreBase` (20 métodos públicos), las constantes (`DEBUG`, `DB_SCHEMA`, tablas, `SQL_FILE_*`) y `anunciar_destino(DEBUG)` (el print PRODUCCIÓN/QA). Los módulos de Danone (49 líneas), Gen (11) y Penafiel (35) ya solo hacen `from repository.core.consultas_postgre import *`, llaman `anunciar_destino(DEBUG)` y definen `class DB_POSTGRE(DBPostgreBase)` con los overrides. Nombres de módulo, métodos y firmas no cambian; Heineken y Holanda siguen importando las constantes de Danone.

* **Mecanismo** (según la sesión): `__init_subclass__` copia cada `staticmethod` heredado a la subclase y lo liga a los globals del módulo del cliente, de modo que `execute_query`, `COOLER_REQUEST` y `SQL_FILE_*` se resuelven en el módulo del cliente en cada llamada (el monkeypatch del `FakeRepo` sigue funcionando). Si a un módulo de cliente le falta un global que usa la base, falla al importar.
* **La base implementa el comportamiento de Gen**, que no tiene overrides.
* **Diferencias reales entre las tres copias** (diff AST de la sesión; no repetí el diff):
  * `insert_update_cooler`: Danone ignora `serie`; Gen y Penafiel, si `serie` no es None/NaN, la usan como `serie_dnn_bnf`. Base = Gen; Danone sobrescribe el hook `_series_insert_update_cooler`. La diferencia no es solo de Penafiel: la que se aparta es Danone.
  * `get_distribuidora_mov`: Danone y Gen devuelven `None` si la fila no trae `distribuidora`; Penafiel devuelve la fila aunque venga vacía. Penafiel sobrescribe.
  * `get_distribuidora_ruta`: Danone devuelve `None` sin `distribuidora`; Gen y Penafiel devuelven la fila. Danone sobrescribe.
  * Los otros 17 métodos son idénticos.
* Matiz: `load_dotenv()` y la lectura de `DEBUG` corren una sola vez (en core), no una por módulo; mismo valor salvo que el entorno cambie entre imports.
* Pruebas: `tests/unit_repository/test_db_postgre_core.py` (47). Verificado en la rama: `pytest -q` → 350 passed, 24 skipped, 1 xfailed.

# Funciones clave

* `save_email_log_init`: insert en `emails_log` con `ON CONFLICT (graph_message_id)`.
* `send_email_request`: insert en `email_request`.
* `send_email_coolers`: insert en `cooler_request` con `WHERE NOT EXISTS`.
* `insert_update_cooler`: update de la fila PENDING y luego insert. Mergeado en `claude/admiring-lovelace-3oh7g0` (rama `claude/e2c-fix-returning`, commits `877f03e`, `dc30f34`): `RETURNING` permite detectar el UPDATE; una fila no PENDING o con serie ya registrada no se inserta y se loguea sin PII "[BASEDATOS] cooler reenviado no aplicado ... requiere revisión: request_code=… row_number=…". Ver [bugs](../riesgos/bugs.md).
* `update_cooler`: update por request y serie. Mergeado en `claude/admiring-lovelace-3oh7g0` (rama `claude/e2c-fix-returning`, commits `877f03e`, `dc30f34`): cuenta filas con `RETURNING`; una serie vacía ya no actualiza filas (antes marcaba REJECTED todas las filas con serie vacía).
* `cooler_request.sql` lo usan `send_email_coolers` e `insert_update_cooler` (danone, gen, penafiel). Mergeado en `claude/admiring-lovelace-3oh7g0` (rama `claude/e2c-fix-returning`, commits `877f03e`, `dc30f34`): su `NOT EXISTS` recibe `(request_code, row_number, serie_fabricante, serie_dnn_bnf)`.
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

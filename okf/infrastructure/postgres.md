---
type: Integration
title: PostgreSQL y Secret Manager
description: Conexión a la base de datos de REPARE, con credenciales desde GCP Secret Manager.
resource: https://github.com/pa70xd/e2c/blob/claude/admiring-lovelace-3oh7g0/infrastructure/database/postgres.py
tags: [postgres, secret-manager]
---

# Conexión

* `get_connection` lee `SECRET_PG_ACC` del entorno y pide usuario y contraseña a Secret Manager en cada llamada.
* Conecta con psycopg2 y `RealDictCursor`.
* Variables: `SECRET_PG_ACC`, `DB_HOST`, `DB_NAME`, `DB_PORT` (5432).
* Sin `sslmode` explícito.

# Red de seguridad contra `NaN` (rama `claude/e2c-lector-nan`, sin mergear)

`execute_query` convierte `NaN`, `pd.NA` y `pd.NaT` de los parámetros en `None` antes de ejecutar (`_sin_nan`, verificado en la rama). Cierra el caso en que un `NaN` de pandas llegaba a PostgreSQL y se guardaba como `'NaN'`. Detalle y límites en [lector](../parsers/lector.md).

# Problemas

* Sin pool. Cada consulta pide el secreto y abre TCP. Lento y con costo de cuota.
* Pierde el tipo de excepción original al re-lanzar (línea 40).
* Imprime `DB_HOST` y `DB_NAME` en logs de depuración en algunos módulos.

Ver [capa de repositorio](../data/capa-repositorio.md).

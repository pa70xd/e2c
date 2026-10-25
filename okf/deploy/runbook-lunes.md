---
type: Runbook
title: Runbook del lunes
description: Pasos cortos para que el dev pruebe el repo con sus credenciales sin tocar código. Todo verificado en el código de la base ef1ebb9, salvo lo marcado.
tags: [runbook, pruebas, debug]
---

# 0. Advertencia: `DEBUG`

**Sin `DEBUG=true`, el import apunta a las tablas de PRODUCCIÓN** (`email_request`, `cooler_request`, `emails_log`). El log lo dice: `[BASEDATOS] dirigido a -> PRODUCCIÓN`. Para probar, define `DEBUG=true` **antes** de cualquier import: usa `emails_log_qa`, `email_request_qa` y `cooler_request_qa`. Verificado en `repository/{danone,gen,penafiel}/consultas_postgre.py:11-26`; los repositorios de Heineken y Holanda importan esas mismas constantes de Danone, así que siguen el mismo modo.

Qué cambia con `DEBUG=true` (verificado en `src/service.py`, `parsers/*.py`):

* Tablas `*_qa` (arriba).
* Se vuelca el correo completo a `email.json` en el cwd (`service.py:157`). Contiene datos del correo: no lo versiones (ya está en `.gitignore`).
* Se exportan las tablas de trabajo a `debug/*.csv` (`export_csv`, `service.py:338` y `:377`).
* Se salta `conversation_exists` (`service.py:229`) y la ventana anti-duplicados `is_duplicate_email` (`:239`, `:320`).
* Se salta `email_init_exist` en Danone, Penafiel, Holanda y Heineken: el mismo correo se puede reprocesar.
* Penafiel fuerza `customer = "penafiel"` (`parsers/penafiel.py:49`).
* No se imprime el cuerpo del correo en el log de entrada (`service.py:169`).

# 1. Instalación y suite offline

```
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest -q
```

Usa `python -m pytest`, no el binario `pytest`: puede ser de otro intérprete. Esperado en la base `9564d90`: **448 passed, 24 skipped, 1 xfailed** (el xfail es "stopwords antes del regex" en Danone; los 24 skip son el SQL contra Postgres de abajo). La suite no usa red, credenciales ni producción. Detalle en [pruebas/harness.md](../pruebas/harness.md).

# 2. Pruebas SQL opcionales (Postgres local desechable)

```
E2C_TEST_PG_DSN="host=/ruta/al/socket port=55432 dbname=postgres user=postgres" python -m pytest -q tests/sql
```

Solo acepta socket Unix o `localhost`/`127.0.0.1`, y crea su propio esquema temporal. Formato exacto en `tests/README.md`. Estas pruebas (`tests/sql/test_cooler_sql.py`) **no se han ejecutado en esta ronda**: es la primera vez que correrán contra una base real.

# 3. Prueba manual de Graph y PostgreSQL, sin procesar correos

Variables existentes (nombres en [despliegue](despliegue.md); no pegues valores en el repo):

* Graph: `CLIENT_ID`, `CLIENT_SECRET`, `TENANT_ID`.
* PostgreSQL: `SECRET_PG_ACC` (nombre del secreto en Secret Manager), `DB_HOST`, `DB_NAME`, `DB_PORT`. Requiere credenciales de GCP aplicables a Secret Manager.
* Google: `MAPS_KEY` (geocodificación).

Comprobar conexión sin tocar datos (solo lectura; sugerencias, escritas a partir del código, no ejecutadas):

```
# PostgreSQL: un SELECT 1 por la misma ruta del repo
DEBUG=true python -c "from infrastructure.database.postgres import execute_query as q; print(q('SELECT 1 AS ok'))"

# Graph: pide un token con MSAL, no lee ni envía correo
DEBUG=true python -c "from infrastructure.graphapi.graphapi import getToken; print('token ok' if getToken() else 'sin token')"
```

No llames a `/receive_mail` con un id de mensaje real ni uses `processMail` sobre el buzón real: procesa el correo, escribe en la base y responde por Graph. Para ejercitar el flujo completo usa los correos sintéticos del harness.

# 4. Variables nuevas, opcionales

* `CORS_ALLOW_ORIGINS`: orígenes separados por comas. Sin ella: `"*"` sin credenciales.
* `GRAPH_CLIENT_STATE`: **no la actives** mientras `subscriptions.py` no envíe `clientState` al crear la suscripción. Con la variable definida, `/receive_mail` descarta toda notificación sin `clientState` coincidente, es decir, todas. `/lifecyclenotif` sigue sin validar.

# 5. Qué cambió de comportamiento en esta ronda

Todo mergeado en `claude/admiring-lovelace-3oh7g0`. Detalle en [bugs](../riesgos/bugs.md).

* `detect_direccion` devuelve `None`: `processMail` ya no revienta, loguea y retorna `None`.
* Regex `aviso`/`avisos` de Danone y Penafiel ahora coinciden (con lookahead que excluye "aviso de privacidad"). Pueden aparecer movimientos que antes se ignoraban.
* `bot.cancelar` de Danone y Penafiel cancela también los coolers PENDING.
* `bot.estatus` de Danone y Penafiel ya no lanza `UnboundLocalError`: responde `msj_fail()`.
* `send_email_coolers` manda series limpias (NaN→None).
* `insert_update_cooler` y `update_cooler` usan `RETURNING`; una fila ACCEPTED reenviada **no se aplica** y sale el log `[BASEDATOS] cooler reenviado no aplicado ... requiere revisión`. Una serie vacía ya no actualiza filas.
* `form_solicitud.sql` sin coma final. `email.json`, `mail.json` y `email_model.json` fuera del índice (siguen en el historial de git).

Además, la Fase 2 (refactor sin cambio de comportamiento, goldens sin diff) está mergeada: `parsers/core/`, `repository/core/`, `bot/commands.py`, `config/data/*.json` y limpieza de código muerto. Ver [deuda técnica](../riesgos/deuda-tecnica.md).

Fase 3 (clasificador): sus ramas aún no están en la base. Cuando lo estén, no exportes `CLASSIFIER_GATE`, `CLASSIFIER_EXTRACT` ni `CLASSIFIER_MIN_CONFIDENCE` al correr la suite: `tests/conftest.py` no las limpia y los goldens correrían con ese proveedor. Ver [núcleo del clasificador](../classifier/core.md).

# 6. Sigue abierto

* Stopwords antes del regex en Danone (reproducido).
* `/lifecyclenotif` sin `clientState`; `subscriptions.py` no envía `clientState`.
* `PARSERS_REPLY[customer]` puede dar `KeyError`.
* Typos visibles a clientes sin corregir: `FECHA SOLCITUD`, `DIREECIÓN`, `Ocurrio`.
* `bot.global` revienta si `created_at` trae `tzinfo` (no verificado con datos reales).
* Un `bot.*` desconocido en Danone no se detecta ni se responde.
* El aviso de "requiere revisión" vive solo en logs; no hay cola de revisión (ticket de la Fase 3). Sigue abierto si un hilo puede cancelar filas ya aceptadas.
* Datos personales en el historial de git y CSV con datos reales; ver [seguridad](../riesgos/seguridad.md).
* Todo el resto de [bugs](../riesgos/bugs.md) marcado "reportado".

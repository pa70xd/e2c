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

**Dependencias nuevas en `requirements.txt`** (UTF-16 LE): `odfpy==1.4.1` (solo sdist), `xlrd==2.0.2` y `anthropic==2.3.0`. Si `pip install` falla con "install_layout" (setuptools de Debian parchado), usa un venv nuevo y ejecuta `pip install -U pip setuptools wheel` antes. En mi contenedor, sin venv, `odfpy` falló al construir la rueda y sin `odfpy`/`xlrd` fallan 6 pruebas (con `xlrd` instalado quedan 2, por `odfpy`); la suma coincide con las 1034 del orquestador. **Verifica `docker build` antes de desplegar** (la imagen usa Python 3.14, que nadie ha probado con estas dependencias).

```
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest -q
```

Usa `python -m pytest`, no el binario `pytest`: puede ser de otro intérprete. Esperado en la base (`6d60cc8`): **1525 passed, 56 skipped, 1 xfailed** (1034/48/1 en `3732c25`). Si faltan `odfpy` o `xlrd` en tu entorno, fallan 2 o más pruebas y la cifra baja (en mi contenedor: 1523 passed + 2 failed, sin `odfpy`) (448/24/1 en `9564d90`, antes de la Fase 3) (el xfail es "stopwords antes del regex" en Danone; los 48 skip son el SQL contra Postgres de abajo). La suite no usa red, credenciales ni producción. Detalle en [pruebas/harness.md](../pruebas/harness.md).

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

Fase 3 (clasificador, mergeada): `classifier/`, `review/` y el proveedor haiku. Por defecto todo usa `regex` y el comportamiento no cambia. `tests/conftest.py` limpia `CLASSIFIER_*` y `ANTHROPIC_API_KEY`, así que exportarlas no altera la suite. Ver [núcleo del clasificador](../classifier/core.md) y [revisión por hilo](../flows/revision-por-hilo.md).

Para repetir la medición de la línea base: `python eval/run_eval.py --provider regex --set eval/sets/sintetico.jsonl` (hoy precisión de gate 0.7419, sale con código 1).

**ADVERTENCIA (PII) — decisión de riesgo del usuario pendiente:** `redact-v2` ya está mergeado (`32e7fbd`) y `classifier.redact.REDACT_VERSION = 2` abre el candado del código (`MIN_REDACT_VERSION = 2` en `classifier/registry.py`; verificado en la base). Sobre los 21 correos reales la sesión midió nombres 53 → 2 y el resto en 0, pero **quedan 2 nombres sin redactar** y 21 correos no prueban cobertura general ([redact](../classifier/redact.md), [correos reales](../pruebas/correos-reales.md)). Usar `CLASSIFIER_SHADOW` o haiku con correos reales manda ese texto a un proveedor externo: el usuario debe aceptar esa fuga residual (o exigir otra capa) antes de encenderlo.

Modo sombra (`CLASSIFIER_SHADOW`, `CLASSIFIER_SHADOW_SAMPLE`; mergeado en la base): ver [sombra](../classifier/sombra.md) para variables, el log `[CLASSIFIER_SHADOW]` y cómo exportarlo y medirlo con `eval/shadow_report.py`. Sigue sujeto a la advertencia de PII de arriba.

**ADVERTENCIA: no actives haiku** (`CLASSIFIER_GATE=haiku` o `CLASSIFIER_EXTRACT=haiku`) **sin antes** correr `eval/smoke_haiku.py` con una key real y sin que la evaluación supere **precisión >= 0.95 en gate** (umbral de [decisiones](../riesgos/decisiones.md)). El evaluador está en la base (`eval/`; ver [evaluador](../pruebas/evaluacion.md)): sobre el set sintético, regex da precisión de gate 0.7419 (no cumple) y haiku, según una sesión con key (no verificado por mí), cumple 1.00 sobre ese mismo set sintético. Falta el set real: con eso sigue sin ser suficiente para activar. Además, `review` solo corre con un proveedor externo y manda avisos reales a REPARE.

En entornos cloud la plataforma descarta las variables `ANTHROPIC_*`: la key se guarda como `E2C_ANTHROPIC_API_KEY` y se pasa con `env -u ANTHROPIC_BASE_URL ANTHROPIC_API_KEY="$E2C_ANTHROPIC_API_KEY" python eval/run_eval.py --provider haiku --set <ruta>` (según la orquestadora; no lo ejecuté). Nunca pegues el valor en el repo.

Variables nuevas, todas opcionales y sin valores en el repo: `CLASSIFIER_GATE`, `CLASSIFIER_EXTRACT` (default `regex`), `CLASSIFIER_MIN_CONFIDENCE` (default 0.7), `ANTHROPIC_API_KEY` (solo para haiku). Nota: `requirements.txt` es UTF-16 LE con CRLF (ahí está `anthropic==2.3.0`): conserva esa codificación si lo editas.

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

# 7. Opcional, solo lectura: armar el set real con backfill

Rama `claude/e2c-backfill` (commit `25a9c34`), **mergeada en la base**. Verificado en la rama: `eval/backfill.py` y `eval/querys/*.sql` existen; el código abre PostgreSQL con `SET TRANSACTION READ ONLY`, tiene una guarda contra sentencias de escritura y `--tablas prod` exige `--confirmo-solo-lectura`; `python -m pytest -q` → 851 passed, 48 skipped, 1 xfailed. Lee los buzones de `config/email_index.json` (Graph solo GET) y los cruza con `emails_log`, `email_request` y `cooler_request` (solo SELECT).

Con tus credenciales de siempre (`CLIENT_ID`, `CLIENT_SECRET`, `TENANT_ID`, `SECRET_PG_ACC`, `DB_HOST`, `DB_NAME`, `DB_PORT`; sin valores aquí):

```
python eval/backfill.py --tablas qa --desde 2026-07-01 --hasta 2026-10-26 --maximo 100
```

* `--tablas prod` exige `--confirmo-solo-lectura`; conviene un usuario de base de solo lectura.
* Salida: `eval/sets/real/backfill_<fecha>.jsonl` (ignorado por git) y `_revision.jsonl` con lo que no tiene evidencia.
* Etiquetas automáticas: filas generadas → `nueva_solicitud`; en un hilo, cambios de filas dentro de 10 minutos → agregar/modificar/cancelar; REPARE con OS adjuntas → categoría `cierre` (no es un tipo del clasificador: `tipo_evento` nulo); sin rastro → `es_os` nulo, **nunca `no_os`**.
* Split ajuste|examen por `--corte` (default: últimos 30 días a examen).
* Evaluar: `python eval/run_eval.py --provider regex --set <archivo> --solo-etiquetados --split examen`.

**Revisar a mano:** todo `_revision.jsonl`; el PII residual en los textos redactados; `thread_ctx` (reconstruido, aproximado); el desfase de huso entre `cooler_request` y `emails_log`.

**Advertencias:**

* **Aún no se ha corrido contra datos reales ni contra el esquema real**: las columnas salen de los SQL del repo y los valores de `direction` se asumen de `detect_direccion`.
* **`redact()` deja un residuo** ([correos reales](../pruebas/correos-reales.md)): el backfill redacta con la v2 (2 nombres de 21 correos pasaron sin redactar). Trátalo como dato sensible: no lo subas al repo ni lo mandes a un proveedor externo sin revisión manual.
* Haiku sigue sin medirse sobre correos reales.

# 8. Orden recomendado para encender lo nuevo (recomendación de la orquestadora)

Todo lo de la Fase 3 y la Fase 4 está **apagado por defecto**. La orquestadora recomienda este orden; yo no lo he probado.

1. **Sombra primero:** `CLASSIFIER_SHADOW=haiku` con `CLASSIFIER_SHADOW_SAMPLE=0.2` (20 % de los correos). La sombra solo registra, nunca decide ni manda correos ([sombra](../classifier/sombra.md)). Requiere `ANTHROPIC_API_KEY` y, por la advertencia de PII de arriba, que el usuario haya aceptado la fuga residual de `redact`. Mide con `eval/shadow_report.py`; recuerda que "acuerdo" no es precisión.
2. **Clientes nuevos, uno por uno:** agregarlos a `E2C_CLIENTES_HABILITADOS` (`imbera`, `torrey`, `kof`, `oxxo`, `oxxo_garantias`) **solo después de revisar sus preguntas abiertas** ([preguntas abiertas](../riesgos/preguntas-abiertas.md)). No se pueden apagar los 4 actuales con ese flag. Cada uno tiene su propio riesgo:
   * KOF: los fixtures no vienen de archivos reales; ajustar alias con el primer correo real; falta activar la suscripción de Graph.
   * Imbera/Torrey: criterio de garantía, formato de OS y sub-cliente sin confirmar.
   * Oxxo: **no lo enciendas mientras la PoC externa siga leyendo el buzón** (duplica OS).
3. Haiku como gate real (`CLASSIFIER_GATE=haiku`) solo con el set real etiquetado y precisión >= 0.95 (ver la advertencia de arriba).

---
type: Testing
title: Harness de pruebas offline
description: Suite pytest sin red ni credenciales, con goldens por parser y xfail estrictos para bugs conocidos. Mergeado en claude/admiring-lovelace-3oh7g0.
tags: [pruebas, harness, golden]
---

# Estado

Mergeado en `claude/admiring-lovelace-3oh7g0` (rama `claude/e2c-harness`). Verificado en la rama del harness: `pytest -q` da `274 passed, 15 xfailed` en ~20 s, sin red ni credenciales.

# Cómo correr

```
pip install -r requirements.txt -r requirements-dev.txt
pytest -q                              # suite completa
pytest -q -rx                          # lista los xfail con su razón
pytest --update-golden [-k nombre]     # regenera goldens; revisar `git diff tests/golden`
python tests/fixtures/build_fixtures.py [--check]   # regenera o verifica Excel y correos sintéticos
```

Detalle en `tests/README.md` de la rama.

# Estructura (bajo `tests/`, más `pytest.ini` y `requirements-dev.txt`)

* `conftest.py`: fuerza `DEBUG=false`, usa un cwd temporal con enlaces a `config/` y `excel_templates/`, y bloquea sockets, DNS, `requests` y PostgreSQL. Las violaciones son `BaseException` y se registran, para que el `except Exception` de producción no las esconda.
* `support/fakes.py`: `FakeRepo` (parchea las funciones públicas de los repositorios de Danone, gen, Penafiel, Heineken y Holanda; registra módulo, función y parámetros), `FakeGraph`, Google Geocoding y Tableau falsos.
* `fixtures/`: Excel y correos inventados (`example.com`), generados por `build_fixtures.py`.
* `golden/*.json`: 59 escenarios con llamadas al repositorio, llamadas externas y respuestas (cuerpo y adjuntos).
* `test_golden_{danone,penafiel,holanda,heineken}.py`: correo nuevo con Excel, hilos (inbound, outbound, `bot.*`, global), rechazados y duplicados.
* `test_unit_email_type.py`, `test_unit_movimientos.py`, `test_smoke.py`, `test_harness_guards.py`, `test_fixtures_sync.py`.
* `test_known_bugs.py`: `xfail` estrictos ligados a [bugs](../riesgos/bugs.md).

# xfail estrictos (15) al momento de la rama

Regex `\a` (4: aviso/avisos × Danone/Penafiel); NaN en `send_email_coolers` (3); `insert_update_cooler` sin `RETURNING` (2); Danone `bot.cancelar`; `detect_direccion` None (2); `bot.estatus` `UnboundLocalError` (2); stopwords antes del regex (1).

**Aviso para la integración**: el harness se basó en la base sin los arreglos de las otras ramas. Al integrar `claude/e2c-fix-mecanicos` (regex), `claude/e2c-fix-parsers` (NaN, Danone `bot.cancelar`) y `claude/e2c-fix-orquestador` (`detect_direccion`), esos `xfail` estrictos pasarán a XPASS y fallarán. Hay que quitarles la marca `xfail` en el mismo merge. Inferido de los diffs, no probado con las ramas combinadas.

# Estado tras los fixes

* `claude/e2c-fix-parsers` (commit `23d6e31`, ya mergeado en la base) convirtió en pruebas normales los xfail de NaN, `bot.cancelar` (Danone y Penafiel) y `bot.estatus`, y actualizó los goldens `*_hilo_bot_cancelar` con la llamada a `cancel_pending_coolers`. Verificado: 281 passed, 9 xfailed. Los 9 restantes: regex `\a` (4, aún sin retirar en esa rama), stopwords (1), `insert_update_cooler` (2), `detect_direccion` None (2).
* Base `04f1ebe` (con las cuatro ramas mergeadas): verificado `292 passed, 3 xfailed`. Los 3 xfail: stopwords (1) e `insert_update_cooler` (2, bug 3, a cargo de fix-returning).
* La base ya trae `a936571`: bug de `detect_direccion` del orquestador pasó a test normal y hay tests de `CORS_ALLOW_ORIGINS` y `GRAPH_CLIENT_STATE`.

# Pruebas de SQL (rama `claude/e2c-fix-returning`, mergeada en la base)

* `tests/sql/test_cooler_sql.py` corre el SQL real de coolers contra un PostgreSQL local si existe `E2C_TEST_PG_DSN` (solo socket Unix o localhost). Sin esa variable, hace skip.
* `tests/sql/test_param_count.py` corre siempre y compara la cantidad de `%s` del SQL con `len(params)`.
* Verificado en esa rama sin `E2C_TEST_PG_DSN`: `303 passed, 24 skipped, 1 xfailed`. **Las pruebas contra PostgreSQL no las ejecuté**; solo corrió lo que no necesita base.

# Pruebas de `parsers/core` (Fase 2)

Rama `claude/e2c-core-parsers` (sin mergear): `tests/unit_core/test_parsers_core.py` (20 pruebas). Verificado en esa rama: `323 passed, 24 skipped, 1 xfailed`; el xfail sigue siendo stopwords. Sin diffs de goldens.

# Sin cubrir

KOF (stub) y código muerto; SQL real (en la base ningún `.sql` corre contra Postgres, `FakeRepo` fija las respuestas; la rama `claude/e2c-fix-returning` agrega `tests/sql/`, ver abajo); Graph real (`getClient`, `sendMail`, renovación de `/lifecyclenotif`); Geocoding y Tableau reales; `.xls`, `.xlsm`, Base64, hojas ocultas; `DEBUG=true`; concurrencia (`MAX(row_number)` de Heineken).

---
type: Testing
title: Harness de pruebas offline
description: Suite pytest sin red ni credenciales, con goldens por parser y xfail estrictos para bugs conocidos. Rama claude/e2c-harness, sin mergear.
tags: [pruebas, harness, golden]
---

# Estado

Existe solo en la rama `claude/e2c-harness`, sin mergear. Verificado: en esa rama `pytest -q` da `274 passed, 15 xfailed` en ~20 s, sin red ni credenciales.

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

**Aviso para la integración**: el harness se basó en la rama base, que no incluye los arreglos de las otras ramas. Al integrar `claude/e2c-fix-mecanicos` (regex), `claude/e2c-fix-parsers` (NaN, Danone `bot.cancelar`) y `claude/e2c-fix-orquestador` (`detect_direccion`), esos `xfail` estrictos pasarán a XPASS y fallarán. Hay que quitarles la marca `xfail` en el mismo merge. Inferido de los diffs, no probado con las ramas combinadas.

# Sin cubrir

KOF (stub) y código muerto; SQL real (ningún `.sql` corre contra Postgres, `FakeRepo` fija las respuestas); Graph real (`getClient`, `sendMail`, renovación de `/lifecyclenotif`); Geocoding y Tableau reales; `.xls`, `.xlsm`, Base64, hojas ocultas; `DEBUG=true`; concurrencia (`MAX(row_number)` de Heineken).

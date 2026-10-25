# Harness de pruebas offline (Fase 1)

Congela el comportamiento **actual** del pipeline (correo → parser → repositorio
→ respuesta) antes de refactorizar. Corre con `pytest`, sin credenciales, sin red
y sin PostgreSQL.

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest -q                                   # todo (≈15 s)
pytest tests/test_golden_danone.py -q       # un cliente
pytest -q -rx                               # además lista los xfail y su razón
```

## Estructura

| Ruta | Qué es |
|---|---|
| `pytest.ini` | `pythonpath = .`, `xfail_strict = true`, marcador `golden`. |
| `requirements-dev.txt` | `pytest` y sus dependencias, con versiones fijas. |
| `conftest.py` | Aísla el entorno, bloquea red/DB, define `harness`, `golden`, `fixtures_for`. |
| `support/fakes.py` | `FakeRepo` (repositorio en memoria), `FakeGraph`, `FakeExternals` (Google Geocoding y Tableau), bloqueos. |
| `support/serialize.py` | JSON determinista de llamadas al repo y resumen de Excel/correo. |
| `support/emails.py`, `support/scenarios.py` | Correos de Graph sintéticos (`Message` real del SDK) y buzones inventados. |
| `fixtures/build_fixtures.py` | Genera `fixtures/<cliente>/*.xlsx` y `correos.json` (todo inventado, `example.com`). |
| `golden/*.json` | Salidas congeladas: llamadas al repo, llamadas externas y correo de respuesta. |
| `test_golden_<cliente>.py` | Danone, Penafiel, Holanda, Heineken: correo nuevo con Excel + hilo (inbound, outbound, `bot.*`). |
| `test_unit_email_type.py` | `validate_email` (tipo de correo), `detect_customer`, `detect_direccion`, duplicados. |
| `test_unit_movimientos.py` | Regex de movimientos/creación/ignorar de Danone y Penafiel y `analizar_proposito`. |
| `test_known_bugs.py` | Bugs de `okf/riesgos/bugs.md` como `xfail(strict=True)`. |
| `test_smoke.py` | `import main` y handshake `validationToken` de `/receive_mail` (y `/lifecyclenotif`). |
| `test_harness_guards.py` | Demuestra que red y PostgreSQL están bloqueados. |
| `test_fixtures_sync.py` | Los fixtures versionados coinciden con `build_fixtures.py` y no usan dominios reales. |

## Cómo funciona (sin tocar producción)

* `conftest.py` fija `DEBUG=false` y corre cada prueba en un directorio temporal con
  enlaces a `config/` y `excel_templates/` (producción lee rutas relativas al cwd y
  crea `Documentos_Adjuntos/`).
* `install_fake_repo` reemplaza con `monkeypatch` **cada función pública** de
  `DB_POSTGRE` (danone, gen, penafiel), `DB_HEINEKEN` y `DB_HOLANDA`. Cada llamada
  queda registrada (módulo, función, parámetros por nombre). Los parámetros con
  `NaN` se escriben `"<NaN>"` para que el golden delate los valores crudos.
* `src.service.getClient` devuelve `FakeGraph`, que sirve el correo y los adjuntos y
  recibe el reply (cuerpo, destinatarios, adjuntos). `requests.get` hacia Google
  Geocoding devuelve una respuesta fija; las funciones de Tableau devuelven `[]`.
* Los buzones de REPARE (`cliente.<cliente>@repare.example.com`) sustituyen a
  `config/email_index.json` solo dentro de las pruebas.
* **Bloqueos**: sockets salientes, DNS, `requests.post/put/...`, `execute_query` y
  `get_connection`. Producción atrapa casi todo con `except Exception`, así que las
  violaciones heredan de `BaseException` y además se anotan: si un golden intenta
  salir, la prueba falla aunque el código lo haya "atrapado".
* Una función del repositorio sin respuesta configurada también falla
  (`UnconfiguredRepoCall`): si producción empieza a usar otra, hay que decidir su respuesta.

## Configurar respuestas del repositorio falso

```python
def test_algo(harness, fx, golden):
    harness.repo.set("get_email_request_status", "COMPLETED")          # valor fijo
    harness.repo.set("email_reply_validate", None)                     # hilo sin solicitud
    harness.repo.set("get_distribuidora_mov", lambda cp, distribuidora: None)  # callable(**params)
    harness.repo.queue("get_email_request_status", ["IN_PROGRESS", "COMPLETED"])  # en orden
    harness.repo.fail("cancel_email_request", RuntimeError("db caída"))  # excepción
    harness.deliver(mensaje, [fx.xlsx("archivo.xlsx")])
    golden.check("nombre_del_escenario", harness.snapshot())
```

Valores por defecto en `FakeRepo._build_defaults`. El CP `99999` no tiene distribuidora.

## Goldens: comparar y regenerar

Cada escenario guarda `tests/golden/<escenario>.json` con `deliveries`, `repo_calls`,
`external_calls` y `replies` (cuerpo del correo y resumen de cada Excel adjunto:
primera hoja completa; las demás, solo título y tamaño).

```bash
pytest                                   # compara; si cambió, muestra el diff
pytest --update-golden                   # reescribe TODOS los goldens
pytest tests/test_golden_danone.py -k bot_ayuda --update-golden   # solo uno
git diff tests/golden                    # revisar SIEMPRE el cambio antes de commitear
```

Un cambio de golden es un cambio de comportamiento: no se regenera para "ponerlo en
verde" sin entender el diff. Para escenarios nuevos: escribe la prueba, corre con
`--update-golden -k <nombre>` y revisa el JSON generado.

## Fixtures sintéticos

```bash
python tests/fixtures/build_fixtures.py          # regenera tests/fixtures/<cliente>/
python tests/fixtures/build_fixtures.py --check  # sale 1 si lo versionado difiere del script
```

No copiar nada de `emails pruebas/`, de los `*.json`/CSV de la raíz ni de correos
reales: solo se tomó de ahí la estructura (encabezados). Dominios `example.com`,
teléfonos 555-01xx.

## Bugs conocidos (`xfail`)

`test_known_bugs.py` afirma el comportamiento **correcto**; hoy falla y queda como
`xfail(strict=True)`. Al corregir el bug la prueba pasa (XPASS) y `strict` la pone en
rojo: se quita el `xfail`, se corre `pytest --update-golden` y se revisa el diff de los
goldens afectados. Ver `pytest -rx` para la lista con la razón.

## Qué no cubre

* **KOF** (`parsers/kof.py` es un stub) y código muerto (`src/attachments.py`,
  `models/service_request.py`, `subscriptions.py`).
* **SQL real**: ningún `.sql` se ejecuta contra PostgreSQL. Solo `send_email_coolers` e
  `insert_update_cooler` corren su código real con un `execute_query` falso (ver
  `test_known_bugs.py`). `FakeRepo` fija las respuestas, así que no detecta cambios en
  el SQL (contadores de `email_request_update.sql`, `RETURNING`, etc.).
* **Graph real**: `getClient`, `sendMail`, `getTemplate`, `send_mail_file`, la
  renovación de `/lifecyclenotif` (msal + PATCH) y `/receive_mail` con payload real
  solo se prueban hasta el límite del doble (handshake y encolado).
* **Geocoding/Tableau reales**: la respuesta es constante (mismo CP para todo). No se
  prueban errores de Google ni coordenadas fuera de rango. Nominatim (`geopy`) no se usa
  en ningún flujo probado.
* **Excel**: solo `.xlsx`. Sin `.xls` (no hay `xlrd` en `requirements.txt`) ni `.xlsm`
  (el lector de Danone/Holanda los detecta pero no los lee: bug reportado). Sin adjuntos
  en Base64 ni hojas ocultas.
* **`DEBUG=true`** (tablas `*_qa`, `export_csv`, volcado `email.json`).
* Concurrencia (`MAX(row_number)` de Heineken) y la ventana anti-duplicados entre procesos.
* Bugs reportados no reproducidos del OKF que dependen de SQL o de datos reales.

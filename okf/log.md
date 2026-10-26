# Historial

## 2026-10-25 · Fase 0 y Fase 1 iniciadas

* Rama de esta sesión: `claude/e2c-okf` (desde `claude/admiring-lovelace-3oh7g0`). Solo esta sesión escribe en `okf/`.
* Sesiones en curso. Orquestadora: session_017Dz5GWFuMfdobetNS5S743. Todas creadas el 2026-10-25.

| Sesión | Modelo | Rama | Alcance | ID |
|---|---|---|---|---|
| okf | sonnet | `claude/e2c-okf` | bundle `okf/` | session_01H9YZYnuM9KepK3YJ7C8Kd7 (en curso) |
| git | haiku | sin rama propia | integración en `claude/admiring-lovelace-3oh7g0` | session_01SnwR9oPhvPBJxF4zBTLsUV (en curso) |
| fix-parsers | opus | `claude/e2c-fix-parsers` | bugs 4, 5 | session_018kxq94j27h98a7b1Qb4i9u (en curso) |
| fix-orquestador | sonnet | `claude/e2c-fix-orquestador` | bugs 1, 6, 8 | session_012yaMA74tXzBbpTkQatosy8 (en curso) |
| fix-mecanicos | haiku | `claude/e2c-fix-mecanicos` | bugs 2, 7, 9 | session_01ToZcSoSRqPyz1cLbqRc37Y (en curso) |
| harness | sonnet | `claude/e2c-harness` | Fase 1 | session_01555AgNz2xRd76uNN5h4J3D (en curso) |
| fix-returning | opus | `claude/e2c-fix-returning` | bug 3 (+ contador `update_cooler`); diagnostica ahora, push después del harness | session_01HapgSRT5RT1R1LKpbsEQSg (en curso) |

## 2026-10-25 · fix-orquestador: Fase 0 lista

* Rama `claude/e2c-fix-orquestador`, sin PR ni merge. Verificado contra el diff (`main.py`, `src/handler.py`, `src/service.py`).
* `detect_direccion` None (bugs.md #6), CORS y `clientState` (seguridad #4 y #1). La numeración 1/6/8 de la orquestadora no coincide con `bugs.md`.
* Variables nuevas opcionales: `CORS_ALLOW_ORIGINS`, `GRAPH_CLIENT_STATE`.
* Pendientes: `PARSERS_REPLY[customer]` puede dar `KeyError`; `/lifecyclenotif` sin validar; `subscriptions.py` sin `clientState`.

## 2026-10-25 · fix-mecanicos: Fase 0 lista

* Rama `claude/e2c-fix-mecanicos`, push hecho, sin PR ni merge. Verificado contra el diff.
* Regex `\a` → `\b` en Danone y Penafiel (bugs.md #1); coma final de `form_solicitud.sql` (bugs.md #10); JSON con datos personales fuera del índice y en `.gitignore` (seguridad #3). La numeración 2/7/9 de la orquestadora no coincide con `bugs.md`.
* Pendiente: el historial conserva los JSON; decidir purga. No se revisó el contenido de los JSON.

## 2026-10-25 · fix-parsers: Fase 0 lista

* Rama `claude/e2c-fix-parsers`, sin PR ni merge. Verificado contra el diff (`parsers/danone.py`, `repository/{danone,gen,penafiel}/consultas_postgre.py`).
* Danone `bot.cancelar` ahora cancela coolers pendientes (bugs.md #5). NaN a PostgreSQL pasa de "reportado" a verificado y corregido (causa en el repositorio).
* Actualización: Penafiel `bot.cancelar` también corregido (commit `a5bd0fc`, verificado en la rama).
* Pendientes nuevos: print de `bot.estatus`, serie float `'123.0'`, `gen` sin llamadores, default a PRODUCCIÓN al importar.

## 2026-10-25 · Notas de la orquestadora

* `DEBUG` no definido = tablas de PRODUCCIÓN (verificado en `repository/danone/consultas_postgre.py:11-16`). Documentado en `deploy/despliegue.md`. El dev debe poner `DEBUG=true` para usar `*_qa`.
* Riesgo anotado en `bugs.md`: el arreglo `\a`→`\b` puede hacer matchear "Aviso de privacidad" en `MOVEMENTS`. Hipótesis; la mide el harness.

## 2026-10-25 · harness: Fase 1 lista

* Rama `claude/e2c-harness`, sin PR ni merge. Reproduje `pytest -q` en un worktree de la rama: 274 passed, 15 xfailed. Documentado en [pruebas/harness.md](pruebas/harness.md) y enlazado en el índice.
* "Stopwords antes del regex" pasa de reportado a reproducido.
* Hallazgos nuevos en `bugs.md`: `bot.global` con `tzinfo`, `bot.*` desconocido en Danone, rechazada por SERIE vacía en Penafiel, rechazadas como PENDING, `DISTINCT` sin `ORDER BY`.
* Aviso: al integrar las ramas de fix, los `xfail` estrictos de bugs ya corregidos pasarán a XPASS y fallarán; hay que quitarles la marca.

## 2026-10-25 · fix-parsers cierre; estado de integración

* `claude/e2c-fix-parsers`, todo pusheado, sin mergear: `bot.estatus` corregido en Danone y Penafiel (`2ab001b`); xfail de NaN, `bot.cancelar` y `bot.estatus` convertidos a tests normales (`23d6e31`). Verificado: 281 passed, 9 xfailed.
* Integración en `claude/admiring-lovelace-3oh7g0` (verificado con `git log`): ya incluye harness, fix-mecanicos y fix-orquestador (merge `16c251a`). Fix-parsers aún no. Estados de esas tres ramas actualizados a "mergeado" en el bundle. fix-orquestador tiene un commit posterior (`efb8ccb`, test) que no vi en la base.
* `msj_fail` duplicada (`messages.py:287` y `:331`) sigue sin corregir; el fix de `bot.estatus` depende de la segunda.

## 2026-10-25 · Estado de integración (base 04f1ebe)

* Base `claude/admiring-lovelace-3oh7g0` en `04f1ebe`: verifiqué `python -m pytest -q` → 292 passed, 3 xfailed.
* Mergeados: harness (`6b13b82`), fix-mecanicos (`dc02a2d`), fix-orquestador (`16c251a` + `efb8ccb`), fix-parsers (`04f1ebe`).
* Corregidos en la base: regex aviso (con lookahead que excluye "aviso de privacidad", verificado en `movimientos_danone.py:164` y `movimientos_penafiel.py:317`), coma de `form_solicitud.sql`, JSON con PII fuera del índice (siguen en el historial), `detect_direccion` None manejado en el llamador (el contrato `None` se mantiene), `CORS_ALLOW_ORIGINS`, `GRAPH_CLIENT_STATE` (opcional; `subscriptions.py` aún no envía `clientState`), NaN en `send_email_coolers`, `bot.cancelar` Danone y Penafiel, `bot.estatus`.
* Pendiente: fix-returning (bug 3 + `NOT EXISTS` de `cooler_request.sql`; fila ACCEPTED reenviada queda sin cambios con log de revisión).
* Reproducido y abierto: stopwords antes de IGNORE en Danone.
* Abiertos sin dueño: `msj_fail` duplicada (conservar la firma sin argumentos, la usa `bot.estatus`), `/lifecyclenotif` sin `clientState`, `PARSERS_REPLY` `KeyError`, `bot.global` con `tzinfo`, `bot.*` desconocido no detectado.
* Runbook: usar `python -m pytest -q`; `DEBUG=true` obligatorio para QA.

## 2026-10-25 · fix-returning: bug 3 y contador de update_cooler

* Rama `claude/e2c-fix-returning` (`877f03e`, `dc30f34`), sin mergear; no está en la base. Verificado contra el diff de SQL y repositorios. En esa rama `pytest -q` → 303 passed, 24 skipped, 1 xfailed (los tests de PostgreSQL local se saltan sin `E2C_TEST_PG_DSN`; no los ejecuté).
* Bug 3 (`insert_update_cooler`) y bug 4 (contador de `update_cooler`) corregidos con `RETURNING`. Corrección al diagnóstico: el duplicado de `row_number` venía de filas ACCEPTED reenviadas, no de la falta de `RETURNING`. `cooler_request.sql` ahora bloquea por `request_code` + `row_number`.
* `update_cooler.sql`: guard de serie vacía (`NULLIF(TRIM(...),'')`), sin filtro por `row_number` (decisión documentada en `bugs.md`).
* Cambio de comportamiento: ACCEPTED reenviada no se inserta ni se sobrescribe; se loguea sin PII.
* Pregunta abierta nueva en `riesgos/preguntas-abiertas.md`. Nueva capa de pruebas SQL en `pruebas/harness.md`.

## 2026-10-25 · Decisión: correcciones sobre filas ACCEPTED

* Decisión del usuario, relayada por la orquestadora: una corrección en un hilo sobre una fila ya ACCEPTED **no se aplica**; va a revisión humana con "requiere revisión". Registrada como respondida en `riesgos/preguntas-abiertas.md`.
* Implementación actual: solo un `print` `[BASEDATOS]` en `insert_update_cooler` (rama `claude/e2c-fix-returning`, mergeada en la base). No hay cola de revisión persistida; ticket para la Fase 3.
* Sigue abierto: si un hilo puede cancelar filas ya aceptadas.

## 2026-10-25 · Fase 0 y Fase 1 cerradas; runbook del lunes

* Base `claude/admiring-lovelace-3oh7g0` en `ef1ebb9`: 303 passed, 24 skipped (SQL sin Postgres), 1 xfailed (stopwords). Mergeado en mi rama.
* Sesiones de código terminadas: git, fix-parsers, fix-orquestador, fix-mecanicos, harness y fix-returning (todas mergeadas en la base; fix-returning por `ef1ebb9`).
* Nuevo [deploy/runbook-lunes.md](deploy/runbook-lunes.md), enlazado en el índice y en `despliegue.md`. Verificado en el código: efectos de `DEBUG`, variables, formato de `E2C_TEST_PG_DSN`. Los comandos de comprobación de Graph y PostgreSQL están escritos a partir del código y no los ejecuté (requieren credenciales).

## 2026-10-25 · Fase 2 iniciada

* Aprobada por el usuario el 2026-10-25 (según la orquestadora). Base de partida: `55acb2f`.
* Regla de la fase: refactor sin cambio de comportamiento; cualquier diff en un golden detiene el trabajo.

| Sesión | Modelo | Rama | ID |
|---|---|---|---|
| core-parsers | sonnet | `claude/e2c-core-parsers` | session_01Dnpx2UrASsnBjt7iY1SejS (en curso) |
| core-repository | opus | `claude/e2c-core-repository` | session_01U1DtW3ZHPe4EuxBceTVHKk (en curso) |
| bot-commands | opus | `claude/e2c-bot-commands` | session_015XVeZawkn9EXDsGo28C8cK (en curso) |
| catalogos | sonnet | `claude/e2c-catalogos` | session_015uwaotKiEb9kcpDcdfmWnf (en curso) |
| limpieza | haiku | pendiente | pendiente: se crea después de mergear las 4 anteriores |

## 2026-10-25 · Decisión: cancelar filas ACCEPTED desde un hilo

* Decisión del usuario, relayada por la orquestadora: pedir en un hilo cancelar un cooler ya ACCEPTED (con OS) **no** lo cancela automáticamente; va a revisión humana, como las correcciones de filas ACCEPTED. Las filas PENDING sí se pueden cancelar. Registrada como respondida en `riesgos/preguntas-abiertas.md`.
* Pendiente (Fase 3): canal de revisión (propuesta: respuesta en el hilo a REPARE con las filas marcadas); cola persistida como ticket aparte. Aún no implementado.

## 2026-10-25 · core-parsers: resumen (Fase 2)

* Rama `claude/e2c-core-parsers`, sin mergear (commits `54ee1b5`, `f9a92db`, `07d2f0e`). Verificado: existen `parsers/core/{tablas,texto,correo}.py` y las utils/readers re-exportan; `pytest -q` en la rama → 323 passed, 24 skipped, 1 xfailed.
* Unificadas `unir_tablas`, `normalizar_texto`, `eliminar_stopwords`, `convertir_html_a_texto` y `detectar_tipo_correo`. Sigue duplicado `process_data`, `safe_filename`, `sql_list`, `normalize`. Documentado en `parsers/gen-base.md` y `riesgos/deuda-tecnica.md`.
* La equivalencia de comportamiento entre copias (AST) es afirmación de la sesión; yo solo verifiqué que los goldens no cambian.

## 2026-10-25 · catalogos: resumen (Fase 2)

* Rama `claude/e2c-catalogos`, sin mergear (commit `8a54b96`). Verificado: `config/data/{distribuidoras,danone_model_line_cat}.json` y `loader.py`; conteos 3471 / 20 / 41 / 851; `pytest -q` → 310 passed, 24 skipped, 1 xfailed. Documentado en `data/catalogos.md`.
* Corrección menor: la cifra de distribuidoras pasa de "~3,472" a 3,471 entradas cargadas (la clave `502635` duplicada colapsa al último valor).

## 2026-10-25 · bot-commands: resumen (Fase 2)

* Rama `claude/e2c-bot-commands`, sin mergear (5 commits, el último `312df12`). Verificado: existen `bot/{commands,perfiles}.py` y `tests/unit_bot/`; `pytest -q` en la rama → 374 passed, 24 skipped, 1 xfailed; sin cambios a `tests/golden` respecto de la base.
* Documentado en `flows/respuesta-y-comandos.md` y `riesgos/deuda-tecnica.md`. También corregí la tabla de comandos, que seguía diciendo que `bot.cancelar` de Danone/Penafiel no cancelaba coolers (corregido en la base).
* Se confirma que `msj_comando_no_reconocido` es inalcanzable (el lector solo detecta palabras reservadas).
* Que el comportamiento es idéntico (matriz antes/después) es afirmación de la sesión; yo solo verifiqué suite y goldens.

## 2026-10-25 · core-repository: resumen (Fase 2)

* Rama `claude/e2c-core-repository`, sin mergear (`351ee40`, `ecaae40`). Verificado: `repository/core/consultas_postgre.py` y los módulos de cliente reducidos; `pytest -q` → 350 passed, 24 skipped, 1 xfailed.
* Documentado en `data/capa-repositorio.md` y `riesgos/deuda-tecnica.md`, con la tabla de diferencias entre Danone, Gen y Penafiel (las diferencias de comportamiento sobreviven como overrides, no se unificaron).
* El diff AST y el mecanismo `__init_subclass__` son afirmación de la sesión; yo verifiqué estructura y suite.

## 2026-10-25 · Fase 2 mergeada; sesión limpieza

* Base `claude/admiring-lovelace-3oh7g0` en `c981a79`: verifiqué `python -m pytest -q` → 448 passed, 24 skipped, 1 xfailed. Mergeada en mi rama.
* Merges: core-parsers `b9bcb90`, catalogos `9b520e8`, bot-commands `0e387c3`, core-repository `c981a79`. Las 4 sesiones de la Fase 2 terminaron.
* Conceptos actualizados a "mergeado": `parsers/gen-base.md`, `data/capa-repositorio.md`, `flows/respuesta-y-comandos.md`, `data/catalogos.md`, `riesgos/deuda-tecnica.md`, `pruebas/harness.md`.
* Nueva sesión: limpieza (haiku) · session_01KH6MyNGZBXmdsy9TTGyijF · `claude/e2c-limpieza` · código muerto, `msj_fail` duplicada, typos en identificadores. En curso.

## 2026-10-25 · limpieza: resumen (Fase 2)

* Rama `claude/e2c-limpieza`, sin mergear (`fa37826`, `085c4b3`, `259aa74`). Verificado: `pytest -q` → 448 passed, 24 skipped, 1 xfailed; en `messages.py` queda solo `msj_fail(self)`; `TIPOS_SERVICIO_VALIDOS` renombrado; borrados confirmados con `git grep`. `tests/golden` sin diff según la sesión (no repetí `--update-golden`).
* Borrado: `detect_purpose`/`union_cap_tables`/`complet_catalog_line` en Danone, `fill_movimiento`/`fill_ruta` en gen, `complet_catalog_line` en Penafiel, 5 métodos de `messages.py`, bloques comentados de `graphapi.py`, primera `msj_fail`. Bug 9 de `bugs.md` marcado corregido.
* No borrado y por qué: `get_categoria_linea` y `fill_movimiento`/`fill_ruta` de Danone (pendientes de confirmar), `src/service.py::flujo` (sí se usa), `src/attachments.py` "debuger". Typos visibles a clientes sin corregir: `FECHA SOLCITUD`, `DIREECIÓN`, `Ocurrio`.
* Sin `Co-Authored-By` en sus commits por regla de su sistema; llevan `Claude-Session`.

## 2026-10-25 · Fase 2 cerrada

* Base `claude/admiring-lovelace-3oh7g0` en `9564d90` (merge de limpieza): verifiqué `python -m pytest -q` → 448 passed, 24 skipped, 1 xfailed. Mergeada en mi rama.
* limpieza (session_01KH6MyNGZBXmdsy9TTGyijF) terminada. Las 5 sesiones de la Fase 2 terminaron.
* Consolidado en los conceptos: `parsers/gen-base.md`, `data/capa-repositorio.md`, `flows/respuesta-y-comandos.md`, `data/catalogos.md`, `riesgos/deuda-tecnica.md` y `services/codigo-muerto.md`. Runbook actualizado a 448/24/1.

## 2026-10-25 · Fase 3 iniciada

* Aprobada por el usuario el 2026-10-25 (según la orquestadora). **Umbral de activación decidido antes de evaluar: precisión >= 0.95 en gate.** Registrado en el concepto nuevo [riesgos/decisiones.md](riesgos/decisiones.md).

| Sesión | Modelo | Rama | ID |
|---|---|---|---|
| classifier-core | opus | `claude/e2c-classifier-core` | session_01MjCtnSt5V8AtZX5biRwjqa (en curso) |
| redact | sonnet | `claude/e2c-redact` | session_014K2t9mPLbMU47mUSfoU7xY (en curso) |
| provider-haiku | sonnet | pendiente | pendiente: arranca cuando los contratos estén estables |
| revision | opus | pendiente | pendiente: ídem |
| eval | sonnet | pendiente | pendiente: ídem |

* El proveedor `jev` queda fuera hasta que haya acceso.

## 2026-10-25 · redact: resumen (Fase 3)

* Rama `claude/e2c-redact` (`0d8fc00`), sin mergear. Verificado: `classifier/redact.py` y `tests/unit_classifier/test_redact.py`; `pytest -q` → 562 passed, 24 skipped, 1 xfailed; prueba mía con texto sintético (correo, teléfono, firma redactados; serie, modelo y folio intactos; idempotente).
* Nuevo concepto [classifier/redact.md](classifier/redact.md), enlazado en el índice.
* Límite anotado: con 10 dígitos sin contexto se redacta como teléfono (privacidad primero); impacto en precisión sin medir.

## 2026-10-25 · Fase 3: más sesiones

* Nuevas, ambas desde `claude/e2c-classifier-core` (`926d693`):

| Sesión | Modelo | Rama | ID |
|---|---|---|---|
| provider-haiku | sonnet | `claude/e2c-provider-haiku` | session_01AAwN4LQL6wjzvahTn2iCMk (en curso) |
| revision | opus | `claude/e2c-revision` | session_0113agkPSN7r2SH56gk1jwWN (en curso) |

* `revision`: canal de revisión (respuesta en el hilo a REPARE por Graph); también agrega el cargador de filas de `cooler_request` para `thread_ctx`. Según la orquestadora.
* Variables opcionales nuevas: `CLASSIFIER_GATE`, `CLASSIFIER_EXTRACT`, `CLASSIFIER_MIN_CONFIDENCE` (las tres verificadas en `classifier/registry.py`; defaults `regex`, `regex`, 0.7) y `ANTHROPIC_API_KEY` (sin verificar). Documentadas en `deploy/despliegue.md`.
* Nota: el registro da `regex` como default del **gate** también; la orquestadora solo mencionó el default de `CLASSIFIER_EXTRACT`.
* Pendiente: eval (sonnet), cuando el usuario mande los correos de ejemplo.

## 2026-10-25 · provider-haiku: resumen (Fase 3)

* Rama `claude/e2c-provider-haiku` (`a27e690`), sin mergear. Verificado: archivos, `anthropic==2.3.0` en `requirements.txt`, modelo `claude-haiku-5-5`, timeout 8 s, 1 reintento, guarda de PII. `pytest -q` → 473 passed, 24 skipped, 1 xfailed **tras instalar `anthropic`** (sin él, `test_haiku.py` falla en recolección).
* Nuevo concepto [classifier/provider-haiku.md](classifier/provider-haiku.md). `ANTHROPIC_API_KEY` pasa a verificada en `despliegue.md`.
* Sin probar con key real (`eval/smoke_haiku.py` pendiente); sin medir precisión.

## 2026-10-25 · classifier-core: resumen (Fase 3)

* Rama `claude/e2c-classifier-core` (`926d693`, `d3fa0b2`), sin mergear. Verificado: estructura, integración en `src/service.py`, `pytest -q` → 560 passed, 24 skipped, 1 xfailed. `--update-golden` sin diff es afirmación de la sesión.
* Nuevo concepto [classifier/core.md](classifier/core.md).
* **Decisión no tomada por el usuario:** CANCELLED/REJECTED a revisión (motivo `estado_no_pending`). Anotada en `riesgos/decisiones.md` como pendiente de confirmación.
* Huecos: sin lector de filas de `cooler_request` (lo agrega `revision`), decisiones del hilo no persistidas, `tests/conftest.py` no limpia `CLASSIFIER_*`, `ultima_decision()` es `ContextVar`. Runbook avisa del tercero.

## 2026-10-25 · revision: resumen (Fase 3)

* Rama `claude/e2c-revision` (`e872203`), sin mergear. Verificado: `review/`, los tres SQL, los métodos de `DBPostgreBase` y los mensajes; `pytest -q` → 492 passed, 48 skipped, 1 xfailed. **No ejecuté** los 48 tests contra Postgres local (540 passed con `E2C_TEST_PG_DSN`, según la sesión).
* Nuevo concepto [classifier/revision.md](classifier/revision.md). Cuatro puntos abiertos de la sesión más dos preguntas a ti, en `riesgos/preguntas-abiertas.md`.
* Solo actúa con `CLASSIFIER_EXTRACT` distinto de `regex`; con el default no corre.

## 2026-10-25 · revision actualizada; Fase 3 parcial en la base

* Base `claude/admiring-lovelace-3oh7g0` en `6d0f897`: ya incluye redact, classifier-core (`ece68b5`, con `281fa4a`) y provider-haiku. Verificado: 710 passed, 24 skipped, 1 xfailed. Mergeada en mi rama.
* revision (`claude/e2c-revision`, `4292106`), sin mergear; verifiqué 740 passed, 48 skipped, 1 xfailed (sin Postgres). Cambios respecto del resumen anterior: alta sin Excel va a revisión (decisión de la orquestadora), cancelar fila ya CANCELLED es idempotente, filas inválidas a revisión (`separar_invalidas`), cargador solo con proveedor externo, `Decision` en `parser.classifier_decision`.
* Resueltos y reflejados en `core.md` y `provider-haiku.md`: `ultima_decision` (ContextVar) eliminada, `extract` recibe el gate, `tests/conftest.py` limpia `CLASSIFIER_*`, `redact` acepta `conservar`.
* Preguntas abiertas de la Fase 3 reducidas a cuatro en `riesgos/preguntas-abiertas.md`.

## 2026-10-25 · Código de la Fase 3 mergeado (base 29881a7)

* Base `claude/admiring-lovelace-3oh7g0` en `29881a7`: verifiqué `python -m pytest -q` → 768 passed, 48 skipped, 1 xfailed. Merges: redact `1e87314`, classifier-core `ece68b5`, provider-haiku `6d0f897`, revision `29881a7`. Las 4 sesiones (classifier-core, redact, provider-haiku, revision) terminaron. Mergeada en mi rama.
* Nuevo flujo [flows/revision-por-hilo.md](flows/revision-por-hilo.md); conceptos de `classifier/` (core, haiku, redact, revision) pasan a "mergeado".
* Runbook: cifras 768/48/1, variables nuevas, advertencia de no activar haiku sin `eval/smoke_haiku.py` con key real y sin precisión >= 0.95 en gate, y `requirements.txt` UTF-16 LE.
* Sigue pendiente: sesión eval (esperan los correos de ejemplo) y las preguntas abiertas de la Fase 3.

## 2026-10-25 · eval: resumen (Fase 3)

* Rama `claude/e2c-eval` (`80fef31`), sin mergear. Verificado: archivos, 67 casos, `pytest -q` → 792 passed, 48 skipped, 1 xfailed; corrí `run_eval.py --provider regex` sobre el set sintético y reproduje la línea base: gate precisión 0.7419 (no cumple 0.95).
* Nuevo concepto [classifier/eval.md](pruebas/evaluacion.md). `decisiones.md` y runbook actualizados: haiku sin medir; set real pendiente.

## 2026-10-25 · eval: documentación movida a pruebas/

* A pedido de la orquestadora, el evaluador se documenta en [pruebas/evaluacion.md](pruebas/evaluacion.md) (antes `classifier/eval.md`), con `EVAL_PRICE_IN` y `EVAL_PRICE_OUT` (verificadas en `eval/run_eval.py`) y la aclaración de que el set sintético no basta para activar. Rama `claude/e2c-eval` aún no está en la base (verificado con `git merge-base`); espero la confirmación de Git del merge 18 antes de mergear la base en mi rama.

## 2026-10-25 · Fase 3 completa en la base (003853d)

* Base `claude/admiring-lovelace-3oh7g0` en `003853d` (merge 18, eval): verifiqué `python -m pytest -q` → 794 passed, 48 skipped, 1 xfailed, y `run_eval.py --provider regex` → precisión de gate 0.7419, NO CUMPLE (sale con código 1). Mergeada en mi rama.
* Estado a "mergeado" en `pruebas/evaluacion.md`, `deploy/despliegue.md`, runbook (cifras 794/48/1, comando de línea base) e índice.
* Abierto: haiku sin medir (no hay key); falta el set real de correos redactados; preguntas de la Fase 3 sin responder.

## 2026-10-26 · Fase 3: parada por falta de key

* Una sesión que no estaba en mi tabla (session_0134X31KeMJTxbNAeRRz2P34) reporta que la Fase 3 está parada: falta `ANTHROPIC_API_KEY` en la sesión de ejecución. No se corrió `eval/smoke_haiku.py` ni la evaluación de haiku. Ya avisó a la orquestadora; se espera que se configure la key. No lo verifiqué: es solo lo que reporta esa sesión; su rol exacto no me consta.
* Consecuencia para el bundle: sin cambios. Haiku sigue sin medir y la activación sigue bloqueada por el umbral de precisión >= 0.95 en gate (ver [evaluación](pruebas/evaluacion.md)).

## 2026-10-26 · Fase 3: haiku medido sobre el sintético (reporte de una sesión)

* La sesión `session_01Jnc7eVXwXyKjsou32zFdCn` informa que corrió el smoke (OK) y la evaluación de haiku sobre el set sintético de 67 casos: gate P=1.00, R=1.00, F1=1.00, 0 FP (cumple 0.95); extract 95.1 % por fila (39/41); caída a regex 1.5 % gate y 2.2 % extract; latencia media 2.0 s, p95 3.2 s; ~128k tokens de entrada y 7.7k de salida. Regex: P=0.74.
* **No lo verifiqué**: no tengo key y no repetí la corrida. Registrado en [pruebas/evaluacion.md](pruebas/evaluacion.md) con esa reserva, más la lectura de que 21 negativos no bastan y de que sin set real no se autoriza la activación. Esto reemplaza lo anotado antes ("parada por falta de key").
* Pendiente que menciona la sesión: los motivos de caída a regex no se imprimen en `run_eval`.

## 2026-10-26 · haiku: confirmación de la orquestadora y truco de la key

* La orquestadora confirma la primera evaluación real de haiku (set sintético, 67 casos): gate P=1.00/R=1.00/0 FP, extract 39/41 con 2 confusiones de tipo (`cancelar_filas`→`modificar_filas`, `cancelar_solicitud`→`estatus`), latencia media 2.0 s (p95 3.2 s), regex 0.74. Veredicto: cumple en el sintético, **NO se activa** (21 negativos, escrito por un modelo, falta el set real). Sigue sin ser verificado por mí.
* Documentado en [pruebas/evaluacion.md](pruebas/evaluacion.md), runbook y `despliegue.md`: la plataforma descarta `ANTHROPIC_*`, la key va en `E2C_ANTHROPIC_API_KEY` y se pasa con `env -u ANTHROPIC_BASE_URL ANTHROPIC_API_KEY="$E2C_ANTHROPIC_API_KEY"` (solo el nombre de la variable).

## 2026-10-26 · eval-set-v2: resumen

* Rama `claude/e2c-eval-set-v2` (`225b457`), sin mergear. Verificado: `sintetico_v2.jsonl` con 41 casos, 18 negativos y 21 filas esperadas; regex: precisión de gate 0.5610 (NO CUMPLE), extract 0/21. Los "4 ambiguos" y que se escribió sin leer los prompts son afirmación de la sesión.
* Haiku no corrido sobre v2. Documentado en [pruebas/evaluacion.md](pruebas/evaluacion.md).

## 2026-10-26 · prompt-v2: resumen (Fase 3)

* Rama `claude/e2c-prompt-v2` (`14ca237`), sin mergear. Verificado: prompts nuevos, `CLASSIFIER_PROMPT_VERSION` en `haiku.py`, cambio en `debe_continuar`; `pytest -q` → 801 passed, 48 skipped, 1 xfailed. Goldens sin diff: afirmación de la sesión.
* Corrección: el outbound (REPARE→cliente) siempre continúa. Documentada en [classifier/core.md](classifier/core.md); prompts v2 en [classifier/provider-haiku.md](classifier/provider-haiku.md).
* Pendiente: medir las 4 corridas sobre `sintetico_v2`; no hay cifras de v2.

## 2026-10-26 · prompt-v2: 4 corridas de haiku (reporte)

* La sesión `session_01XYEn1Va9jA5mi2dFpmyQfG` reporta 4 corridas (v1/v2 × sintetico/sintetico_v2); tabla completa en [pruebas/evaluacion.md](pruebas/evaluacion.md). Resumen: sobre `sintetico`, precisión de gate 0.9787 (v1) y 0.9783 (v2); sobre `sintetico_v2`, 0.9167 (v1) y 0.9200 (v2) → **no cumple 0.95**. v2 no mejora de forma medible. Caída a regex del gate hasta 19.5 % en `sintetico_v2`.
* **No verificado por mí.** Hay una discrepancia sin explicar con la primera evaluación (1.00 vs 0.9787 en el mismo set). Rama `claude/e2c-prompt-v2` (`301461b`) sin mergear.

## 2026-10-26 · eval-diagnostico: resumen

* Rama `claude/e2c-eval-diagnostico` (`719504c`), sin mergear. Verificado: 798 passed, 48 skipped, 1 xfailed; el evaluador imprime FN, errores de tipo, caídas a regex y métricas solo-proveedor/sin ambiguos (probado con regex: 37 casos sin ambiguos).
* Reporte de la sesión (no verificado, requiere key): haiku v1 sobre `sintetico_v2` gate 0.9167, 7 caídas a regex (17.1 %) todas `confianza_baja`; solo-haiku P 1.00, R 0.944; extract 18/21; hipótesis `filas_no_cargadas` descartada. Mi inferencia: el incumplimiento viene de las caídas, no de haiku; anotada como inferencia en [pruebas/evaluacion.md](pruebas/evaluacion.md).
* Pendiente de decisión: ajustar prompt o `CLASSIFIER_MIN_CONFIDENCE` (0.7), con el riesgo de sobreajustar al set que se mide.

## 2026-10-26 · Decisiones: duda a revisión, modo sombra y backfill; sesiones nuevas

* Registradas en [riesgos/decisiones.md](riesgos/decisiones.md): (1) en un hilo, haiku con confianza baja va a revisión humana, no a regex (en init sigue a regex); (2) se aprueba el modo sombra; (3) se aprueba el backfill de solo lectura con etiquetas automáticas del histórico (las series que entran y salen de la sábana).
* Sesiones nuevas: sombra + duda→revisión (opus) · session_01E9q7mT1muX4Ayrtc2z8Bg9 · `claude/e2c-sombra` (variables opcionales `CLASSIFIER_SHADOW`, `CLASSIFIER_SHADOW_SAMPLE`); backfill (sonnet) · session_01F6oVDx61MHMbSLJoHLekdz · `claude/e2c-backfill`. En curso.
* El usuario compartió 21 correos reales (.eml); la orquestadora los analiza localmente y no se documenta su contenido. Esperando el resumen redactado.

## 2026-10-26 · Análisis de 21 correos reales (resumen redactado)

* Documentado en [pruebas/correos-reales.md](pruebas/correos-reales.md) y `riesgos/bugs.md`, sin contenido de los correos. Cifras de la orquestadora (no tengo los .eml): regex precisión de gate 0.81, 15/21 tipos, 0/5 filas.
* Verificado en el código: `es_asunto_holanda` exige el asunto exacto, `detect_direccion` mira solo el `To:`, la etapa sale del prefijo "RE:", y `email_index.json` mapea cuatro clientes más un buzón personal. No copié direcciones al bundle.
* **Bloqueante:** `redact()` dejó pasar 53 nombres, 7 direcciones, 6 coordenadas, 1 URL de mapa, 2 correos y 3 montos. No activar `CLASSIFIER_SHADOW` ni haiku con correos reales hasta mergear `redact-v2` (`session_01GRj3nHJi8AeCXJdsKvwAEY`). Advertencia añadida al runbook.
* Sesión nueva: fix-holanda-indice · session_01WjEJyAUVg4bTSoA1wXQ8HM · `claude/e2c-fix-holanda-indice` (variable opcional `E2C_TEST_MAILBOX`). Decisión de alcance de buzones pendiente con el usuario.

## 2026-10-26 · backfill: resumen

* Rama `claude/e2c-backfill` (`25a9c34`), sin mergear. Verificado: `eval/backfill.py`, flags, transacción `READ ONLY`, guarda contra escritura, `--tablas prod` exige confirmación; `pytest -q` → 851 passed, 48 skipped, 1 xfailed. No se corrió contra datos ni esquema reales (afirmación de la sesión y consistente con el código).
* Añadido el paso 7 (opcional, solo lectura) al runbook y la sección en [pruebas/evaluacion.md](pruebas/evaluacion.md). Riesgo anotado: el backfill redacta con `redact()` v1, insuficiente; tratar el set como sensible hasta `redact-v2`.

## 2026-10-26 · fix-holanda-indice: resumen

* Rama `claude/e2c-fix-holanda-indice` (`330763f`, `707d0b5`), sin mergear. Verificado: `pytest -q` → 829 passed, 48 skipped, 1 xfailed; `es_asunto_holanda` acepta "Casos REPARE" con fecha o sufijo y rechaza frase embebida o texto tras la fecha; `email_index.json` queda con 4 claves; `E2C_TEST_MAILBOX` se lee en `src/email_type.py`.
* Documentado en `parsers/holanda.md`, `clients/reglas-por-cliente.md`, `infrastructure/subscriptions.md`, `deploy/despliegue.md`, `riesgos/bugs.md` y `riesgos/seguridad.md`.
* PII: quité del bundle la dirección personal de `clients/index.md`. El historial de git sigue conteniéndola; `subscriptions.py` aún la tiene hardcodeada (según la sesión).
* Sigue abierto: el lector de Holanda no acepta `.xlsm`.

## 2026-10-26 · Corrección de privacidad en el bundle

* Por indicación de la orquestadora: reemplacé las direcciones de correo personales/de remitente que estaban escritas en `clients/index.md` (ya hecho en el commit anterior) y en `infrastructure/graph-api.md` por marcadores (`<buzón de pruebas personal>`, `<remitente>`). No se repiten aquí. Quedan los buzones de rol `cliente.*` del dominio de REPARE como mapeo funcional; revisión pendiente si se prefieren también omitirlos.
* Documentado: el buzón de pruebas pasa a `E2C_TEST_MAILBOX` (rama `claude/e2c-fix-holanda-indice`, por mergear). **Siguen dos usos funcionales de esa dirección en código** (verificado): `EMAIL_SENDER` en `infrastructure/graphapi/graphapi.py:44` y el default de `MAIL` en `src/handler.py:26`. No se tocaron porque afectan el envío por Graph; el dev decide moverlos a una `MAIL` obligatoria.
* El historial de git conserva las direcciones antiguas.

## 2026-10-26 · sombra + duda→revisión: resumen

* Rama `claude/e2c-sombra` (`7b86977`, `ca00f10`), sin mergear. Verificado: `classifier/shadow.py`, `eval/shadow_report.py`, `msj_clasificacion_dudosa`, `Decision.motivo_revision`; `pytest -q` → 872 passed, 48 skipped, 1 xfailed. El comportamiento del thread/timeout, el contenido del log y los comandos de exportación son descripción de la sesión.
* Nuevo concepto [classifier/sombra.md](classifier/sombra.md); fila de "clasificación dudosa" en [flows/revision-por-hilo.md](flows/revision-por-hilo.md); variables en `deploy/despliegue.md`; runbook al día.
* Bloqueo vigente: sombra con correos reales espera `redact-v2`. Límite: el init de Danone y Penafiel no pasa por la sombra.

## 2026-10-26 · Fase 4 iniciada: Imbera, KOF, Torrey y Oxxo

* Aprobada por el usuario (según la orquestadora). Registrada en [riesgos/decisiones.md](riesgos/decisiones.md): entran Imbera, KOF, Torrey y Oxxo; **Oxxo apagado por defecto** (PoC automatizada fuera del repo, riesgo de duplicado). Oxgar no figura: sigue fuera de alcance.

| Sesión | Modelo | Rama | ID |
|---|---|---|---|
| lector-excel + flag de clientes | sonnet | `claude/e2c-lector-excel` | session_01Hij48ERTesNyVTDdyWeyPH (en curso) |
| KOF | opus | `claude/e2c-kof` | session_01UEpkYP4VR6wHShaKZL9biN (en curso) |
| Imbera + Torrey | opus | `claude/e2c-imbera-torrey` | session_01RhmhtzWqP56UdKESrWfBkt (en curso) |
| Oxxo (parser de plantillas sin LLM) | sonnet | `claude/e2c-oxxo` | session_01E8Gh3qWbaaqB8cksMj4s5n (en curso) |

* Variable nueva `E2C_CLIENTES_HABILITADOS` (sin ella solo corren los 4 clientes actuales); aún no verificada en código. Orden: lector-excel primero; KOF e Imbera/Torrey se adaptan a él; Oxxo en paralelo.

## 2026-10-26 · redact-v2: resumen

* Rama `claude/e2c-redact-v2` (`ae4da5e`), sin mergear. Verificado: `pytest -q` → 993 passed, 48 skipped, 1 xfailed; eval regex sin cambios (0.7419); prueba propia con texto inventado (cabeceras, saludo, firma, coordenadas, URL de mapa y monto redactados; folio, serie y modelo intactos; idempotente).
* Documentado en [classifier/redact.md](classifier/redact.md): marcadores nuevos, criterios y límites.
* **El bloqueo de sombra/haiku con correos reales sigue vigente:** falta re-probar con los 21 correos reales dentro del contenedor y mergear la rama.

## 2026-10-26 · lector-excel + flag de clientes: resumen (Fase 4)

* Rama `claude/e2c-lector-excel` (`b3e308e`, `717cb96`), sin mergear. Verificado: `parsers/core/lector.py`, `odfpy==1.4.1` en `requirements.txt`, mapeo de 5 buzones nuevos en `email_index.json`, `E2C_CLIENTES_HABILITADOS` en `src/email_type.py`. `pytest -q` → 922 passed, 2 failed, 48 skipped, 1 xfailed: los 2 fallos por no poder instalar `odfpy` en este contenedor (la sesión reporta 924 passed).
* Documentado en [parsers/lector.md](parsers/lector.md), `clients/index.md`, `deploy/despliegue.md`, `decisiones.md`, `bugs.md`.
* Dos cosas que señalo: `oxogar`→`oxxo_garantias` quedó mapeado sin estar en la lista aprobada (apagado por el flag), y `.xls` necesita `xlrd` que no está en `requirements.txt`. Los lectores actuales no están migrados al lector común.

## 2026-10-26 · modelos: bug 2 corregido en parte

* Rama `claude/e2c-modelos` (`ee6c3a0`, `a8cf448`), sin mergear. Verificado: `parsers/core/modelos.py`, `eval/cobertura_modelos.py`, `eval/reportes/modelos_ambiguos.md` (46 ambiguos de 803); `pytest -q` → 916 passed, 48 skipped, 1 xfailed.
* **Discrepancia con el resumen:** el commit `a8cf448` (posterior al resumen) cambia 5 goldens, regenera 4 fixtures y agrega un párrafo "Modelos sin resolver" al correo de respuesta; el resumen decía que los goldens no cambiaron. Documentado en `riesgos/bugs.md`.
* Pendiente de decisión: cómo llevar el motivo a REPARE (el párrafo de aviso es una solución parcial en la rama).

## 2026-10-26 · modelos: resumen final

* La sesión confirma `a8cf448` como final, aprobada por la orquestadora para merge. Cambios a goldens a propósito (5). Documentado en `riesgos/bugs.md`: sigue "corregido en parte" por los 46 ambiguos; `eval/cobertura_modelos.py` sin correr con datos reales; Penafiel sin catálogo propio (pregunta para el usuario).

## 2026-10-26 · lector-excel: resumen final (Fase 4)

* Rama `claude/e2c-lector-excel` (`b0758f7`, `41eafbf` además de los anteriores), aprobada y en merge. Verificado: `xlrd==2.0.2` en `requirements.txt`, `xlwt==1.3.0` en `requirements-dev.txt`, `sheet.visibility == 0` en los lectores de Danone y gen. Cifra de la sesión: 928 passed, 48 skipped, 1 xfailed.
* Dos bugs de `.xls` encontrados y corregidos (xlrd ausente y `sheet_visibility`); corrijo lo que había escrito antes ("`.xls` necesita `xlrd` que no está"). Pendiente: verificar el build de `odfpy` con Python 3.14 (imagen del Dockerfile); en mi contenedor falló al construir la rueda.

## 2026-10-24

* Creación del bundle OKF del repositorio `e2c` (rama `claude/admiring-lovelace-3oh7g0`).
* Fuentes: lectura completa del repo por áreas (entrada y src, parsers, repository, config) y verificación manual de los hallazgos marcados como verificados.
* Los hallazgos marcados como "reportado" vienen de análisis estático y no se reprodujeron en ejecución.
* Sin cambios de código. Ningún archivo del repo fue modificado fuera de `okf/`.

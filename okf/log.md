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
* Implementación actual: solo un `print` `[BASEDATOS]` en `insert_update_cooler` (rama `claude/e2c-fix-returning`, sin mergear). No hay cola de revisión persistida; ticket para la Fase 3.
* Sigue abierto: si un hilo puede cancelar filas ya aceptadas.

## 2026-10-25 · Fase 0 y Fase 1 cerradas; runbook del lunes

* Base `claude/admiring-lovelace-3oh7g0` en `ef1ebb9`: 303 passed, 24 skipped (SQL sin Postgres), 1 xfailed (stopwords). Mergeado en mi rama.
* Sesiones de código terminadas: git, fix-parsers, fix-orquestador, fix-mecanicos, harness y fix-returning (todas mergeadas en la base; fix-returning por `ef1ebb9`).
* Nuevo [deploy/runbook-lunes.md](deploy/runbook-lunes.md), enlazado en el índice y en `despliegue.md`. Verificado en el código: efectos de `DEBUG`, variables, formato de `E2C_TEST_PG_DSN`. Los comandos de comprobación de Graph y PostgreSQL están escritos a partir del código y no los ejecuté (requieren credenciales).

## 2026-10-24

* Creación del bundle OKF del repositorio `e2c` (rama `claude/admiring-lovelace-3oh7g0`).
* Fuentes: lectura completa del repo por áreas (entrada y src, parsers, repository, config) y verificación manual de los hallazgos marcados como verificados.
* Los hallazgos marcados como "reportado" vienen de análisis estático y no se reprodujeron en ejecución.
* Sin cambios de código. Ningún archivo del repo fue modificado fuera de `okf/`.

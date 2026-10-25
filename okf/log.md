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

## 2026-10-24

* Creación del bundle OKF del repositorio `e2c` (rama `claude/admiring-lovelace-3oh7g0`).
* Fuentes: lectura completa del repo por áreas (entrada y src, parsers, repository, config) y verificación manual de los hallazgos marcados como verificados.
* Los hallazgos marcados como "reportado" vienen de análisis estático y no se reprodujeron en ejecución.
* Sin cambios de código. Ningún archivo del repo fue modificado fuera de `okf/`.

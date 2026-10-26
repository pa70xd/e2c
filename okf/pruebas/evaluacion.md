---
type: Module
title: Evaluador del clasificador (eval/)
description: Mide gate y extract por proveedor (regex|haiku) contra un set etiquetado y compara la precisión de gate con el umbral 0.95. Mergeado en claude/admiring-lovelace-3oh7g0.
tags: [classifier, eval, umbral, fase-3]
---

# Estado

Rama `claude/e2c-eval` (commit `80fef31`), **mergeada en la base** `claude/admiring-lovelace-3oh7g0` (`003853d`). Verificado en la rama: existen `eval/{run_eval,metrics,smoke_haiku}.py`, `eval/schema.md`, `eval/README.md`, `eval/sets/sintetico.jsonl` (67 casos) y `tests/unit_eval/`; `python -m pytest -q` en la rama → 792 passed, 48 skipped, 1 xfailed; en la base `003853d` → **794 passed, 48 skipped, 1 xfailed**. `eval/sets/real/` está en `.gitignore`.

# Cómo correrlo

```
python eval/run_eval.py --provider regex --set eval/sets/sintetico.jsonl
ANTHROPIC_API_KEY=... python eval/run_eval.py --provider haiku --set <ruta>
```

Opciones: `--umbral`, `--json <ruta>`. Costo de haiku: define `EVAL_PRICE_IN` y `EVAL_PRICE_OUT` (USD por millón de tokens, solo nombres; verificado en `eval/run_eval.py`); sin ellas el reporte no calcula costo (según `eval/README.md`). Cada caso pasa por `classifier.redact` y luego por `classifier.decidir` (la ruta de producción, con validación y caída a regex). Los reportes imprimen solo ids de caso. Si la precisión de gate queda bajo el umbral, el script sale con código 1 (lo comprobé con `--provider regex`: salió 1). Sin key, `haiku` avisa "ANTHROPIC_API_KEY no está definida" y no hace llamadas (comprobado; el código de salida de 0 lo reporta la sesión).

# Formato del set (`eval/schema.md`)

JSONL con `id`, `fuente` (sintetico|real), `etapa` (init|reply), `asunto`, `cuerpo` ya redactado, `thread_ctx` opcional (filas con `row_number`, series y `status`; decisiones previas) y `esperado` `{es_os, tipo_evento, filas[accion, row_number, series opcionales]}`. Extras opcionales: `cliente` y `direccion` (el gate regex de init depende del cliente). Las series solo se comparan si la etiqueta trae la clave.

El set sintético son 67 casos inventados (`example.com`) que cubren los 8 tipos de evento: firma con aviso de privacidad, gracias, seguimiento, reenvío y duplicado, cancelar fila ACCEPTED, modificar PENDING, referencias como "la segunda fila", texto citado, inyección de prompt, Holanda y Heineken. El set real vive fuera del repo; el procedimiento (redactar, revisar a mano, etiquetar) está en `eval/README.md`.

# Resultado medido: línea base regex

Corrí el evaluador sobre el set sintético en la rama:

* Gate (regex): **precisión 0.7419, recall 1.0000, F1 0.8519** (TP 46, FP 16, FN 0, TN 5). **No cumple** el umbral de 0.95 ([decisiones](../riesgos/decisiones.md)). Los 16 falsos positivos son `no_os` y `duplicado` que regex marca como OS: en hilos todo cae a `modificar_filas`, y en init de Holanda y Heineken el gate delega al parser.
* Extract (regex): exactitud por fila 0.0 (0 de 41), porque regex devuelve `[]` y las filas salen del Excel.
* Latencia: media 11.2 ms, p95 0.7 ms.

# Correr con key en entornos cloud

La plataforma descarta las variables `ANTHROPIC_*` en la sesión de ejecución. La key de la organización se guardó con otro nombre, `E2C_ANTHROPIC_API_KEY` (solo el nombre; el valor no va al repo), y se pasa así:

```
env -u ANTHROPIC_BASE_URL ANTHROPIC_API_KEY="$E2C_ANTHROPIC_API_KEY" python eval/run_eval.py --provider haiku --set <ruta>
```

(`-u ANTHROPIC_BASE_URL` quita la URL base del proxy de la plataforma. Comando según la orquestadora; no lo ejecuté.)

# Por qué el set sintético no basta para activar

Activar un proveedor externo exige correos reales redactados (set real fuera del repo) y una corrida con key real. El set sintético sirve para regresión y para comparar proveedores, no para decidir la activación (lo señala también la orquestadora).

# Resultado reportado: haiku sobre el set sintético (NO verificado por mí)

Lo reportan la sesión `session_01Jnc7eVXwXyKjsou32zFdCn` y la orquestadora (2026-10-26), con una key de la organización del usuario; yo no la usé y **no repetí la medición**. No he visto el reporte completo.

* Smoke (`eval/smoke_haiku.py`): OK.
* Gate (67 casos sintéticos): precisión 1.00, recall 1.00, F1 1.00, 0 falsos positivos; el umbral de 0.95 **se cumple** sobre este set.
* Extract: 95.1 % por fila (39 de 41).
* Caída a regex: gate 1.5 %, extract 2.2 %.
* Latencia: media 2.0 s, p95 3.2 s. Tokens: ~128 k de entrada, ~7.7 k de salida.
* Comparación: regex en el mismo set, precisión 0.74 con 16 falsos positivos (no cumple).
* Dos confusiones de tipo de evento en extract: `cancelar_filas` → `modificar_filas` y `cancelar_solicitud` → `estatus`.
* Pendiente señalado por la sesión: los motivos de la caída a regex no se imprimen en `run_eval`.

**Veredicto técnico (orquestadora): cumple el umbral en el sintético, pero NO se activa.** El set es sintético, tiene solo 21 negativos y lo escribió un modelo; falta el set real.

**Cómo leerlo:** el set sintético tiene 21 negativos, así que una precisión de 1.00 es compatible con un error real bastante mayor. Este resultado **no basta para activar** haiku: hacen falta correos reales redactados (set real) y la corrida con key sobre ellos. Que el umbral se cumpla en el sintético no equivale a cumplirlo en producción.

# Set sintético v2 (rama `claude/e2c-eval-set-v2`, sin mergear)

Rama `claude/e2c-eval-set-v2` (commit `225b457`): `eval/sets/sintetico_v2.jsonl`, 41 casos inventados "difíciles" con 18 negativos y 21 filas esperadas (verifiqué esas tres cifras). La sesión dice que son 4 ambiguos y que lo escribió sin leer los prompts ni `haiku.py`, para no sesgarlo; eso no lo puedo comprobar.

* **Regex (medido por mí en la rama):** precisión de gate 0.5610, recall 1.0000, F1 0.7188 — **no cumple** 0.95; extract 0 de 21 filas. Regex marca todo como OS.
* **Haiku sobre v2:** al escribir esto no estaba corrido; ahora hay 4 corridas reportadas (sección siguiente de resultados). Lo que sigue explica por qué importaba: v2 tiene casi el doble de proporción de negativos (18 de 41 frente a 21 de 67) y fue escrito sin ver el prompt.
* La sesión no pudo correr `pytest` en su contenedor (falta `msgraph`); el evaluador sí corrió en mi entorno.
* Sigue siendo sintético: no sustituye el set real.

# Haiku: 4 corridas de prompt v1 vs v2 (reporte de la sesión prompt-v2, NO verificado por mí)

Reporta `session_01XYEn1Va9jA5mi2dFpmyQfG` (2026-10-26; v1 = gate-v1/extract-v2, v2 = gate-v2/extract-v3; el prompt no se ajustó tras ver resultados). No las repetí: no uso la key. El detalle vive en la rama `claude/e2c-prompt-v2` (`301461b`, sin mergear).

| Set | Prompt | Gate precisión | Recall | F1 | Cumple 0.95 | Extract por fila | Caída a regex (gate) |
|---|---|---|---|---|---|---|---|
| sintetico (67) | v1 | 0.9787 | 1.0000 | 0.9892 | sí | 0.951 | 3.0 % |
| sintetico (67) | v2 | 0.9783 | 0.9783 | 0.9783 | sí | 0.951 | 4.5 % |
| sintetico_v2 (41) | v1 | 0.9167 | 0.9565 | 0.9362 | **no** | 0.905 | 19.5 % |
| sintetico_v2 (41) | v2 | 0.9200 | 1.0000 | 0.9583 | **no** | 0.952 | 14.6 % |

* **Nota:** esta corrida da en `sintetico` precisión 0.9787 con v1, no 1.00 como en el reporte anterior de la primera evaluación; la diferencia no está explicada (el LLM no es determinista, o cambió el código/prompt entre corridas). No la puedo resolver sin repetir.
* Sin los 4 casos ambiguos de `sintetico_v2` (cálculo a mano de la sesión): v1 0.9524, v2 0.9545, que cumplen por poco.
* Latencia media ~2.0-2.1 s, p95 3.2-3.6 s. Tokens de entrada de v2: +67 a +88 % frente a v1 (parte cacheada).
* **Conclusión de la sesión:** v2 no mejora de forma medible (dentro del ruido). Persisten `imb-noos-01`, `hol-dup-01` y 2 casos `nueva_solicitud` → `modificar_filas`.
* **Lectura:** sobre el set más difícil, haiku **no cumple** el umbral de 0.95. Además la caída a regex del gate (hasta 19.5 %) contamina la medición: parte de las respuestas que cuentan son de regex, no de haiku. La activación sigue sin autorizarse.
* ~~Pendiente: `run_eval` no imprime falsos negativos, errores de tipo ni el motivo de la caída a regex~~ Resuelto en la rama `claude/e2c-eval-diagnostico` (ver abajo).

# Diagnóstico del evaluador (rama `claude/e2c-eval-diagnostico`, sin mergear)

Commits `60d4376` y `719504c`, sobre `sintetico_v2`. Verificado en la rama: `pytest -q` → 798 passed, 48 skipped, 1 xfailed; `run_eval.py` ahora imprime falsos negativos, errores de `tipo_evento`, cada caída a regex (id, etapa, motivo) y métricas de gate **solo-proveedor** y **sin ambiguos**. Con regex en `sintetico_v2` comprobé que imprime "Gate sin casos ambiguos (37 casos)": precisión 0.5405, recall 1.0 (TP 20, FP 17, FN 0, TN 0), lo que confirma 4 casos ambiguos de 41. Regex en el set completo: TP 23, FP 18, TN 0.

**Corrida de haiku v1 sobre `sintetico_v2`, reportada por la sesión (NO verificada por mí, necesita key):**

* Gate: precisión 0.9167, recall 0.9565, **no cumple 0.95**.
* **7 caídas a regex (17.1 %), todas por `gate:confianza_baja`**; 0 caídas de extract.
* **Solo-haiku (34 casos, sin las caídas): precisión 1.00, recall 0.944.**
* Extract: 18 de 21 filas.
* Hipótesis descartada: `haiku_filas_no_cargadas`. Los 24 casos `reply` traen `thread_ctx.filas`.

**Inferencia mía, no de la sesión:** las cifras sugieren que el incumplimiento de 0.95 viene de las respuestas de baja confianza que caen a regex (que acierta poco), no de errores de haiku en las que contesta. Habría que confirmarlo; cambiar `CLASSIFIER_MIN_CONFIDENCE` mueve esas caídas y también el riesgo de aceptar respuestas dudosas.

**Pendiente de decisión:** ajustar el prompt o `CLASSIFIER_MIN_CONFIDENCE` (hoy 0.7). Ajustar sobre el mismo set que se mide infla el resultado; el umbral se fijó antes de evaluar ([decisiones](../riesgos/decisiones.md)).

# Backfill para el set real (rama `claude/e2c-backfill`, sin mergear)

Commit `25a9c34`. `eval/backfill.py` arma el set real de solo lectura desde los buzones históricos y etiqueta automáticamente con lo que quedó en `emails_log`/`email_request`/`cooler_request` (la señal: las series que entran y salen de la sábana). Comando, etiquetas y revisión manual en el [runbook, paso 7](../deploy/runbook-lunes.md). Verificado: lectura en transacción `READ ONLY` y suite 851 passed, 48 skipped, 1 xfailed; **no se corrió contra datos ni esquema reales**. Las etiquetas son automáticas y aproximadas: "sin rastro" no es `no_os`, así que no hay negativos fiables sin revisión manual. Medir con ese set no autoriza la activación mientras `redact()` siga insuficiente.

# Lo que NO está medido

* Haiku sobre correos reales (sobre `sintetico_v2` ya hay una medición reportada, arriba). No existe el set real (espera los correos de ejemplo).
* Costo en USD: depende de `EVAL_PRICE_IN` y `EVAL_PRICE_OUT`; el reporte que me llegó solo da tokens.
* El set sintético son 67 casos; es una estimación gruesa.
* La línea base regex mide la lógica heredada, no una activación nueva: el umbral aplica a activar un proveedor externo.

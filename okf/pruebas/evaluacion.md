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

# Lo que NO está medido

* Haiku sobre correos reales. No existe el set real (espera los correos de ejemplo).
* Costo en USD: depende de `EVAL_PRICE_IN` y `EVAL_PRICE_OUT`; el reporte que me llegó solo da tokens.
* El set sintético son 67 casos; es una estimación gruesa.
* La línea base regex mide la lógica heredada, no una activación nueva: el umbral aplica a activar un proveedor externo.

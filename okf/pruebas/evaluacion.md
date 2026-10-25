---
type: Module
title: Evaluador del clasificador (eval/)
description: Mide gate y extract por proveedor (regex|haiku) contra un set etiquetado y compara la precisión de gate con el umbral 0.95. Rama claude/e2c-eval, sin mergear.
tags: [classifier, eval, umbral, fase-3]
---

# Estado

Rama `claude/e2c-eval` (commit `80fef31`), **sin mergear**. Verificado en la rama: existen `eval/{run_eval,metrics,smoke_haiku}.py`, `eval/schema.md`, `eval/README.md`, `eval/sets/sintetico.jsonl` (67 casos) y `tests/unit_eval/`; `python -m pytest -q` → **792 passed, 48 skipped, 1 xfailed**. `eval/sets/real/` está en `.gitignore`.

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

# Por qué el set sintético no basta para activar

Activar un proveedor externo exige correos reales redactados (set real fuera del repo) y una corrida con key real. El set sintético sirve para regresión y para comparar proveedores, no para decidir la activación (lo señala también la orquestadora).

# Lo que NO está medido

* **Haiku no se ha corrido**: sin key, ni `eval/smoke_haiku.py` ni la evaluación con `--provider haiku`. No hay ninguna cifra de precisión de haiku.
* Solo hay set sintético; el set real no existe todavía (espera los correos de ejemplo). Con 67 casos y 21 negativos (16 FP + 5 TN), la precisión es una estimación gruesa: no sustituye una evaluación con correos reales.
* La línea base regex mide la lógica heredada, no una activación nueva: el umbral aplica a activar un proveedor externo.

---
type: Module
title: Modo sombra (classifier/shadow.py)
description: Corre un segundo gate en paralelo, solo para registrar su decisión y compararla con la real; nunca bloquea, aplica ni manda correos. Mergeado en la base (claude/e2c-sombra).
tags: [classifier, sombra, shadow, fase-3]
---

# Estado

Rama `claude/e2c-sombra` (commits `7b86977` y `ca00f10`), **mergeada en la base** (`27ccc22`). Verificado en la rama: existen `classifier/shadow.py`, `eval/shadow_report.py` y `msj_clasificacion_dudosa` en `messages.py`; `python -m pytest -q` → **872 passed, 48 skipped, 1 xfailed**. Aprobado por el usuario el 2026-10-26 ([decisiones](../riesgos/decisiones.md)).

> **Decisión de riesgo del usuario pendiente:** `redact-v2` está mergeado y `REDACT_VERSION = 2` abre el candado, pero quedan 2 nombres de 21 correos reales sin redactar ([redact](redact.md)). La sombra manda texto redactado a un proveedor externo; el usuario debe aceptar esa fuga residual antes de activarla con correos reales.

# Variables (opcionales)

* `CLASSIFIER_SHADOW`: vacía por defecto. Nombre de un proveedor (p. ej. `haiku`). Si es distinto de `CLASSIFIER_GATE`, corre ese gate en sombra en un thread daemon (timeout de 10 s, aplicando la redacción) y **solo registra**. Con `haiku` necesita `ANTHROPIC_API_KEY`.
* `CLASSIFIER_SHADOW_SAMPLE`: 0.0 a 1.0, default 1.0. Fracción de correos que van a la sombra, para controlar el costo.

Ambas se leen en `classifier/registry.py`/`shadow.py` (verificado que se mencionan ahí; el comportamiento del thread y del timeout es descripción de la sesión).

# Log

`[CLASSIFIER_SHADOW] {json}` con el hash del `message_id`, `customer`, etapa, dirección, decisión real y de la sombra (proveedor, `es_os`, `tipo_evento`, `confidence`, `motivo_caida`), `coinciden`, `latencia_ms` y `prompt_version`. Sin PII, según la sesión.

# Cómo medir (sin ejecutar por mí)

```
gcloud logging read 'resource.type="cloud_run_revision" AND textPayload:"[CLASSIFIER_SHADOW]"' --project=<p> --freshness=7d --limit=100000 --format=json > shadow.json
python eval/shadow_report.py shadow.json [--json]
```

El reporte da acuerdo global, por cliente, por etapa y por `tipo_evento`, la matriz real vs sombra, motivos de caída y latencia p50/p95. Estos comandos están copiados del mensaje de la sesión; no los ejecuté.

**Ojo:** "acuerdo" entre la decisión real y la sombra no es precisión. Si la decisión real es regex (precisión baja en hilos), un alto acuerdo no prueba que haiku acierte. Para precisión hacen falta etiquetas ([backfill](../pruebas/evaluacion.md)).

# Límite

El init de Danone y Penafiel **no pasa por la sombra**, porque su gate corre dentro del parser (`analizar_proposito`).

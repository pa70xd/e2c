---
type: Module
title: Proveedor Haiku (classifier/providers/haiku.py)
description: Implementación de gate() y extract() del clasificador con Claude Haiku 5.5. Opcional; el default sigue siendo regex. Rama claude/e2c-provider-haiku, sin mergear.
tags: [classifier, haiku, llm, fase-3]
---

# Estado

Rama `claude/e2c-provider-haiku` (commit `a27e690`), sobre `claude/e2c-classifier-core` (`926d693`), **sin mergear**. Verificado en la rama: `classifier/providers/haiku.py`, `classifier/prompts/{gate,extract}.md`, `tests/unit_classifier/test_haiku.py` y `eval/smoke_haiku.py` existen; `anthropic==2.3.0` está en `requirements.txt`. `python -m pytest -q` → **473 passed, 24 skipped, 1 xfailed**, pero solo después de instalar `anthropic` a mano: sin el paquete, la recolección de `test_haiku.py` falla con `ModuleNotFoundError`. En un entorno ya instalado con el `requirements.txt` de la rama no debería pasar.

# Cómo se activa

* `CLASSIFIER_GATE=haiku` y/o `CLASSIFIER_EXTRACT=haiku`. El default sigue siendo `regex`.
* `ANTHROPIC_API_KEY` (opcional). Sin ella, `haiku` no se usa: la decisión cae a regex con el log `[HAIKU] ANTHROPIC_API_KEY no configurada`. Nunca pegues su valor en el repo.
* Modelo: `claude-haiku-5-5`. Timeout 8 s, 1 reintento del SDK, `max_tokens` 4096, esfuerzo `low` (constantes de `haiku.py`).

# Contrato y salvaguardas

* **Entrada: solo texto redactado** (ver [redact](redact.md)). Si el asunto o el cuerpo traen correo o teléfono, no se llama a la API y la decisión cae a regex (`haiku_pii_sin_redactar`). Esta guarda detecta correo y teléfono; no puede detectar nombres.
* Prompts en español: `gate-v1` y `extract-v1`, con 9 y 8 ejemplos sintéticos según la sesión. La parte fija (instrucciones + ejemplos) lleva `cache_control`; el hilo y el correo van aparte.
* Salida estructurada con enums cerrados de `classifier/contracts.py`; la validación final es de `classifier/validate.py`.
* Fallas: timeout, error de API, rechazo o JSON inválido lanzan excepción y la decisión cae a regex.
* Logs sin PII: operación, versión de prompt, `tipo_evento`, `confidence`, `latencia_ms` y tokens leídos de caché.

# Límites y pendientes

* `extract()` no recibe el `tipo_evento` del gate: el modelo lo infiere y `validate` exige coherencia.
* **No probado con una key real.** El smoke (`eval/smoke_haiku.py`) está pendiente; todas las pruebas usan un cliente mockeado. No hay medición de precisión contra el umbral de 0.95 (ver [decisiones](../riesgos/decisiones.md)).
* La sesión lista como pendiente que exista `classifier/redact.py` en la base; hoy vive en la rama `claude/e2c-redact`.

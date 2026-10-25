---
type: Module
title: Núcleo del clasificador (classifier/)
description: Contratos, validación, registro de proveedores, proveedor regex e integración del gate en el flujo de correos. Rama claude/e2c-classifier-core, sin mergear.
tags: [classifier, contratos, gate, fase-3]
---

# Estado

Rama `claude/e2c-classifier-core` (commits `926d693`, `d3fa0b2`), desde `claude/admiring-lovelace-3oh7g0`, **sin mergear**. Verificado en la rama: existen `classifier/{contracts,validate,registry,__init__}.py`, `classifier/providers/regex.py` y `tests/unit_classifier/`; `python -m pytest -q` → **560 passed, 24 skipped, 1 xfailed** (448 de la base + 112 nuevos); la corrida no dejó cambios en el árbol. `src/service.py` importa `classifier` y llama `classifier_permite` (Danone/Penafiel pasan por `analizar_proposito`, que delega en `classifier.gate_proposito`).

# Contratos (`classifier/contracts.py`)

* `gate(subject, body_redacted, thread_ctx) -> GateResult{es_os, tipo_evento, confidence, detalle}`.
* `tipo_evento` cerrado: `nueva_solicitud`, `agregar_filas`, `modificar_filas`, `cancelar_filas`, `cancelar_solicitud`, `estatus`, `duplicado`, `no_os`.
* `extract(body_redacted, thread_ctx) -> [RowExtraida{accion agregar|modificar|cancelar, folio, serie_fabricante, serie_dnn_bnf, modelo, tipo_servicio, direccion, row_number}]`.
* `ThreadCtx{etapa init|reply, customer, direccion, request_code, decisiones, filas}`; `filas` es una lista de `FilaGuardada{row_number, status, series}`, o `None` si no se cargaron.
* `Decision` con `filas_aplicables` y `filas_revision`. Interfaz de redacción: `redact(text) -> str` (ver [redact](redact.md)).

# Validación (`classifier/validate.py`)

Esquema, enums, confianza mínima, coherencia `es_os` ↔ tipo, evento contra etapa y que la fila referida exista. Los errores son códigos sin PII.

# Registro y variables (`classifier/registry.py`)

`CLASSIFIER_GATE` y `CLASSIFIER_EXTRACT` (default `regex`), `CLASSIFIER_MIN_CONFIDENCE` (default 0.7). Opcionales. `haiku` y `jev` están registrados; `haiku` se implementa en [provider-haiku](provider-haiku.md), `jev` sigue sin implementar. Sin `classifier/redact.py`, el stub lanza `NotImplementedError` y todo cae a regex: no sale texto sin redactar (garantía de la sesión).

# Proveedor regex (`classifier/providers/regex.py`)

* init de Danone y Penafiel: `analizar_proposito_regex` (la lógica de antes, renombrada).
* init de Holanda y Heineken: deja pasar (decide el parser por asunto/Excel, como antes).
* reply: siempre `es_os`; `bot.cancelar` → `cancelar_solicitud`; otros `bot.*` → `estatus`; sin palabra → `modificar_filas` (regex no distingue agregar de modificar).
* `extract` devuelve `[]`.

# Integración (`src/service.py`)

El gate se aplica a **todos** los mensajes de hilo (antes del parser REPLY) y al init de Holanda y Heineken. Si un gate externo dice `no_os` o `duplicado`, se descarta. Los comandos internos (`reply_to_bot`/`bot`) siempre siguen. Si el clasificador falla, el flujo sigue como antes (log `[CLASSIFIER][ERROR]`). Con el proveedor regex por defecto, `--update-golden` no dejó diff (según la sesión).

# Reglas de filas

* Modificar o cancelar una fila **ACCEPTED nunca se aplica**: va a `filas_revision` con el comentario "requiere revisión". Es la [decisión del usuario](../riesgos/decisiones.md).
* PENDING se aplica.
* **Decisión de la sesión, no del usuario:** las filas CANCELLED y REJECTED también van a revisión (motivo `estado_no_pending`), por precaución. Falta que el usuario la confirme o la cambie.
* `cancelar_solicitud` manda a revisión las filas no PENDING del hilo.

# Huecos (reportados por la sesión)

1. No hay función en `repository/**` que lea las filas de `cooler_request` por `request_code`. El enchufe es `classifier.registrar_cargador_contexto(fn)`; sin él, toda modificación o cancelación por fila de un proveedor externo cae a regex. La sesión `revision` dice que agrega ese cargador.
2. Las decisiones previas del hilo no se persisten (`ThreadCtx.decisiones` queda vacío).
3. `tests/conftest.py` no limpia `CLASSIFIER_*`: si alguien las exporta, los goldens fuera de `tests/unit_classifier` correrían con ese proveedor. **Relevante para el [runbook](../deploy/runbook-lunes.md)**: no exportar esas variables al correr la suite.
4. `ultima_decision()` es un `ContextVar`: solo se ve dentro de la misma tarea de `processMail`.

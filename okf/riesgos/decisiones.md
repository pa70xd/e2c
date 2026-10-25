---
type: Decision Log
title: Decisiones del proyecto
description: Decisiones tomadas por el usuario y relayadas por la orquestadora, con fecha. Las preguntas aún abiertas están en preguntas-abiertas.md.
tags: [decisiones, fase-3]
---

# Fase 3: clasificador

* **Fase 3 aprobada** por el usuario el 2026-10-25 (según la orquestadora).
* **Umbral de activación: precisión >= 0.95 en gate.** Decidido **antes** de evaluar, para que el resultado de la evaluación no mueva el umbral.
* Sesiones creadas (en curso): classifier-core (opus) · `claude/e2c-classifier-core`; redact (sonnet) · `claude/e2c-redact`.
* Pendientes, arrancan cuando los contratos estén estables: provider-haiku (sonnet), revision (opus), eval (sonnet).
* El proveedor `jev` queda fuera hasta que haya acceso.
* El "gate" es la decisión es_os/tipo_evento del clasificador (ver [núcleo](../classifier/core.md)). La precisión se mide con el [evaluador](../classifier/eval.md): sobre el set sintético, regex da 0.7419 (no cumple); haiku no se ha medido. El set real aún no existe.

# Filas ACCEPTED en hilos (2026-10-25)

* Una corrección sobre una fila ya ACCEPTED **no se aplica**; va a revisión humana con "requiere revisión".
* Pedir cancelar un cooler ya ACCEPTED (con OS) **no** lo cancela automáticamente; va a revisión humana. Las filas PENDING sí se pueden cancelar desde un hilo.
* Pendiente (Fase 3): canal de revisión (propuesta: respuesta en el hilo a REPARE con las filas marcadas). La cola persistida es un ticket aparte. Detalle en [preguntas abiertas](preguntas-abiertas.md).

# Pendiente de confirmación del usuario

* classifier-core decidió **por precaución, sin consultar al usuario**, que las filas CANCELLED y REJECTED también van a revisión humana (motivo `estado_no_pending`), además de ACCEPTED. No es una decisión del usuario. Ver [núcleo del clasificador](../classifier/core.md).

# Fase 2

* Refactor sin cambio de comportamiento; cualquier diff en un golden detiene el trabajo.

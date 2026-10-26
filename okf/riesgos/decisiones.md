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
* El "gate" es la decisión es_os/tipo_evento del clasificador (ver [núcleo](../classifier/core.md)). La precisión se mide con el [evaluador](../pruebas/evaluacion.md): sobre el set sintético, regex da 0.7419 (no cumple) y haiku, según una sesión con key (no verificado por mí), 1.00 (cumple). El set real aún no existe: el umbral se decidió para la activación, así que la medición sobre el sintético no la autoriza.

# Filas ACCEPTED en hilos (2026-10-25)

* Una corrección sobre una fila ya ACCEPTED **no se aplica**; va a revisión humana con "requiere revisión".
* Pedir cancelar un cooler ya ACCEPTED (con OS) **no** lo cancela automáticamente; va a revisión humana. Las filas PENDING sí se pueden cancelar desde un hilo.
* Pendiente (Fase 3): canal de revisión (propuesta: respuesta en el hilo a REPARE con las filas marcadas). La cola persistida es un ticket aparte. Detalle en [preguntas abiertas](preguntas-abiertas.md).

# Decisiones del usuario del 2026-10-26 (relayadas por la orquestadora)

1. **Duda de haiku en un hilo → revisión humana, no regex.** En un hilo, si haiku duda (confianza baja), la decisión va a revisión humana. En **init** sigue cayendo a regex, porque decide el Excel.
2. **Se aprueba el modo sombra** (el clasificador corre en paralelo sin decidir). Variables nuevas opcionales: `CLASSIFIER_SHADOW` y `CLASSIFIER_SHADOW_SAMPLE` (nombres según la orquestadora; aún no verificadas en código).
3. **Se aprueba el backfill de solo lectura con etiquetas automáticas a partir del histórico:** las series que entran y salen de la sábana son la señal. Sin escritura en la base.

Implementación: (1) y (2) en la rama `claude/e2c-sombra` (ver [sombra](../classifier/sombra.md) y [revisión por hilo](../flows/revision-por-hilo.md)); (3) en `claude/e2c-backfill` (ver [evaluación](../pruebas/evaluacion.md)). Ninguna está mergeada. Sesiones: sombra + duda→revisión `session_01E9q7mT1muX4Ayrtc2z8Bg9`; backfill `session_01F6oVDx61MHMbSLJoHLekdz`.

Contexto: el usuario compartió 21 correos reales (.eml). La orquestadora los analiza localmente, sin salir del contenedor, y **no se documenta su contenido** aquí; el resumen redactado llegará después.

Esto responde la decisión pendiente de "ajustar prompt o `CLASSIFIER_MIN_CONFIDENCE`" de la [evaluación](../pruebas/evaluacion.md) solo en parte: define qué pasa con las respuestas dudosas en un hilo, pero no cambia el umbral de confianza ni el de precisión 0.95.

# Alcance de buzones (pendiente con el usuario)

`config/email_index.json` solo mapea danone, holanda, kdrp y hnk; Imbera, oxxo, oxogar, torrey y kof no entran al sistema. Falta decidir si se incorporan. Ver [correos reales](../pruebas/correos-reales.md).

# Pendiente de confirmación del usuario

* classifier-core decidió **por precaución, sin consultar al usuario**, que las filas CANCELLED y REJECTED también van a revisión humana (motivo `estado_no_pending`), además de ACCEPTED. No es una decisión del usuario. Ver [núcleo del clasificador](../classifier/core.md).

# Fase 2

* Refactor sin cambio de comportamiento; cualquier diff en un golden detiene el trabajo.

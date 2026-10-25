---
type: Open Questions
title: Preguntas abiertas
description: Decisiones de negocio o técnicas pendientes, documentadas en el código o detectadas en el análisis.
tags: [pendientes, negocio]
---

# Holanda

* ¿Confirmar modelo sin catálogo ("CONFIRMAR MODELO")?
* ¿Quién es el responsable de remitentes autorizados? La lista está vacía con TODO.
* ¿MERMA se debe leer en outbound? Hoy no.
* ¿CASO2 se reutiliza o se corrige? Por confirmar.

# Heineken

* ¿Canal D2D a CBU: qué mapeo es el correcto?
* Si `NUMERO CASO` o `FOLIO` llega lleno, ¿va a Folio u Orden?
* Cambios (`RETIRO POR CAMBIO`, `CAMBIO DE ENF`): ¿debe generar también la entrega del equipo de reemplazo?

# Danone y Penafiel

* ¿Por qué `TRASLADO` no está en Danone? Penafiel sí lo incluye.
* ¿Modelo, línea y categoría entran en esta etapa? Hoy no se llenan para equipos de competencia y la decisión de integrar el CRM no está tomada.

# Repo

* ¿KOF se habilita? Requiere reglas, buzón y registro en los mapas de parsers.
# Respondidas

Ver también [decisiones](decisiones.md).

* **¿Un hilo puede cancelar filas ya ACCEPTED (con OS)?** No automáticamente. Decisión del usuario del 2026-10-25, relayada por la orquestadora: va a revisión humana, igual que las correcciones sobre filas ACCEPTED. Las filas PENDING sí se pueden cancelar desde un hilo. Pendiente para la Fase 3: el canal de revisión (propuesta: respuesta en el hilo a REPARE con las filas marcadas); la cola persistida queda como ticket aparte. No implementado: hoy `bot.cancelar` actúa sobre coolers PENDING y la solicitud; no verifiqué cómo trata filas ACCEPTED.
* **¿Una corrección por hilo puede modificar filas ACCEPTED?** No. Decisión del usuario del 2026-10-25, relayada por la orquestadora: la corrección sobre una fila ya ACCEPTED no se aplica y va a revisión humana con el comentario "requiere revisión". Hoy se implementa solo como un `print` `[BASEDATOS]` en `insert_update_cooler` (rama `claude/e2c-fix-returning`, mergeada en la base). Pendiente: ese aviso vive únicamente en los logs y no hay cola de revisión persistida; queda como ticket de la Fase 3.
* ¿Se elimina el historial de `email.json` y demás datos reales?
* ¿Se cambia el webhook a validación por `clientState`?

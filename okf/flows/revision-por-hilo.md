---
type: Flow
title: Revisión por hilo
description: Qué pasa cuando un correo de hilo pide agregar, modificar o cancelar filas de una solicitud: qué se aplica, qué va a revisión humana y cómo se avisa a REPARE.
tags: [flujo, clasificador, review, hilo]
---

# Estado

Mergeado en `claude/admiring-lovelace-3oh7g0` (merge `29881a7`, rama `claude/e2c-revision`). Verificado en la base: `review/{contexto,aplicador,canal}.py` existen y `python -m pytest -q` → 768 passed, 48 skipped, 1 xfailed. Los 48 skip son los tests contra PostgreSQL local; no los ejecuté. Módulo: [revisión](../classifier/revision.md).

# Cuándo corre

Solo si `CLASSIFIER_GATE` o `CLASSIFIER_EXTRACT` es distinto de `regex`. Con el default (`regex`) no hay consultas nuevas ni cambia nada. Además: dirección inbound, correo **sin Excel adjunto** (con Excel decide el parser, como hoy), `request_code` resuelto por el hilo, etapa `reply` y un tipo de evento `agregar_filas`, `modificar_filas`, `cancelar_filas` o `cancelar_solicitud`.

# Reglas por fila

| Situación | Resultado |
|---|---|
| Fila **PENDING** | Se modifica o cancela. Si el UPDATE no toca nada (carrera con un outbound), va a revisión (`estado_cambio`). |
| Fila **ACCEPTED** | Nunca se aplica; va a revisión con "requiere revisión". **Decisión del usuario** (2026-10-25). |
| Fila **CANCELLED** o **REJECTED** | Va a revisión (`estado_no_pending`). **Pendiente de que el usuario lo confirme**: hoy es decisión de la sesión classifier-core. |
| Cancelar una fila **ya CANCELLED** | No hace nada: "sin cambios" (`ya_cancelada`), sin aviso a REPARE. |
| **Alta sin Excel** (desde texto) | No se inserta; va a revisión: "alta sin Excel; requiere datos completos". Decisión de la orquestadora, sin confirmar por el usuario: una fila sin distribuidora ni geocodificación rompe las sábanas y Tableau. |
| Alta con serie ya registrada | "Sin cambios", sin aviso. |
| Fila **inválida o inexistente** | Va a revisión con su código como motivo (`classifier.validate.separar_invalidas`); el resto del correo se aplica. |
| **Clasificación dudosa** en un hilo (el gate externo cae **solo** por confianza baja, `< CLASSIFIER_MIN_CONFIDENCE`) | Decisión del usuario (2026-10-26): no se aplica nada por texto; la `Decision` queda con `motivo_revision = "clasificación dudosa"` y sin filas. Si es un inbound sin Excel, se avisa a REPARE en el hilo ("requiere revisión", `msj_clasificacion_dudosa`). El parser corre igual que hoy. Mergeado en la base. |
| `cancelar_solicitud` | Cancela las filas PENDING; la solicitud solo se cancela si no quedó nada en revisión (primero `update_email_request`, luego `cancel_email_request`). |

En **init** la duda cae a regex (decide el Excel). Las demás caídas (timeout, API, sin key, PII, salida inválida) siguen cayendo a regex sin aviso.

Los errores globales, una fila que no es `RowExtraida`, una acción desconocida o `filas_no_cargadas` hacen caer **toda** la decisión a regex.

# Aviso a REPARE

Dos correos en el mismo hilo, con `reply_mail_onl_text`: primero el aviso de revisión (`msj_revision_repare`: incluye "requiere revisión" y una tabla con fila, serie, acción y motivo) y luego el resumen de cambios (`msj_cambios_hilo`). Ambos llegan a `host_email`, el buzón REPARE del cliente, como cualquier respuesta de los parsers. No hay cola de revisión persistida: es un ticket aparte. Ver [decisiones](../riesgos/decisiones.md) y [preguntas abiertas](../riesgos/preguntas-abiertas.md).

# Límites

* Con Excel adjunto no se atiende lo que pida el texto.
* Los avisos solo viven en el correo; si nadie lo atiende, no queda registro persistente.

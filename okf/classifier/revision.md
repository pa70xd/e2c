---
type: Module
title: Revisión por hilo (review/)
description: Aplica en cooler_request los cambios pedidos en un hilo (solo filas PENDING) y manda a revisión humana, por correo a REPARE, todo lo demás. Mergeado en claude/admiring-lovelace-3oh7g0.
tags: [classifier, review, hilo, fase-3]
---

# Estado

Rama `claude/e2c-revision` (commits `e872203`, `2358cd5`, `4292106`), **mergeada en la base** `claude/admiring-lovelace-3oh7g0` (`29881a7`). Las reglas por fila y el aviso están en el flujo [revisión por hilo](../flows/revision-por-hilo.md); esta página describe los módulos. Verificado en la rama: existen `review/{contexto,aplicador,canal}.py`, los tres SQL nuevos, `get_cooler_rows`, `update_pending_cooler_row`, `cancel_pending_cooler_row` en `repository/core/consultas_postgre.py` (`DBPostgreBase`) y los mensajes `msj_revision_repare` y `msj_cambios_hilo`. Base verificada: `python -m pytest -q` → **768 passed, 48 skipped, 1 xfailed**. Los 48 skip son los tests contra PostgreSQL local; **no los ejecuté**. La sesión reporta 788 passed, 1 xfailed con `E2C_TEST_PG_DSN` local y que los goldens no cambiaron.

# Cuándo actúa

`review` solo atiende un mensaje si se cumple **todo** esto (según la sesión):

* `CLASSIFIER_EXTRACT` es distinto de `regex`. **Con el default `regex` no se consulta el hilo y nada de esto corre** (los goldens no cambian).
* El cargador del contexto solo consulta `cooler_request` si `CLASSIFIER_GATE` o `CLASSIFIER_EXTRACT` es distinto de `regex` (hay un test que lo verifica, según la sesión): con el default no hay consultas nuevas por correo.
* Dirección inbound, sin adjuntos (con Excel decide el parser, como hoy), `request_code` resuelto (sale de `email_reply_validate`, por hilo) y etapa `reply`.
* Tipo de evento `agregar_filas`, `modificar_filas`, `cancelar_filas` o `cancelar_solicitud`, y hay filas que aplicar o revisar.

# Piezas

* `contexto.py`: `cargador(repo)` lee las filas de `cooler_request` por `request_code`, sin PII. Se registra al importar `service` (resuelve el hueco 1 de [núcleo](core.md)).
* `aplicador.py`: `aplicar(decision, ctx, repo)`.
* `canal.py`: `debe_atender` y `atender`.
* SQL: `cooler_rows_by_request.sql`; `update_pending_cooler_row.sql` (`COALESCE(NULLIF(TRIM(%s),''), col)` en folio, series, modelo, tipo de servicio y dirección); `cancel_pending_cooler_row.sql`. Los dos UPDATE filtran por `request_code` + `row_number` + `status='PENDING'` y usan `RETURNING`. Las tablas siguen a `DEBUG` (`*_qa`).
* `src/service.py`: `classifier_evaluar` devuelve `(permite, decision, ctx)`; la `Decision` viaja en `parser.classifier_decision` y `ultima_decision` ya no existe.

# Reglas

* Las filas **PENDING** se modifican o cancelan fila por fila. Si el UPDATE no toca nada (carrera con un outbound), la fila va a revisión con motivo `estado_cambio`.
* **Van a revisión:** ACCEPTED, CANCELLED, REJECTED (salvo que se pida cancelar una ya CANCELLED, ver abajo), filas inválidas o inexistentes y errores del repositorio. (ACCEPTED es [decisión del usuario](../riesgos/decisiones.md); CANCELLED/REJECTED siguen [pendientes de confirmación](../riesgos/decisiones.md).)
* **Alta desde texto (sin Excel): ya no se inserta**; va a revisión con motivo "alta sin Excel; requiere datos completos", porque una fila sin distribuidora ni geocodificación rompe las sábanas y Tableau. Decisión de la orquestadora, no del usuario. Una serie ya registrada queda "sin cambios" y no genera aviso.
* **Cancelar una fila ya CANCELLED es idempotente:** queda en "sin cambios" (motivo `ya_cancelada`) y no avisa a REPARE.
* **Filas inválidas o inexistentes:** `classifier.validate.separar_invalidas` las manda a `filas_revision` con su código como motivo y el resto del correo se aplica. Siguen cayendo a regex los errores globales, una fila que no es `RowExtraida`, una acción desconocida y `filas_no_cargadas`.
* `cancelar_solicitud`: cancela las PENDING; la solicitud solo se cancela si no quedó nada en revisión (primero `update_email_request`, después `cancel_email_request`).

# Canal de revisión

Se manda con `reply_mail_onl_text` en el mismo hilo: primero el aviso de revisión (`msj_revision_repare`: incluye "requiere revisión" y una tabla con fila, serie, acción y motivo) y después la respuesta (`msj_cambios_hilo`). Ambos llegan a `host_email`, el buzón REPARE del cliente, como cualquier respuesta de los parsers. Esto es la propuesta de la Fase 3 ("respuesta en el hilo a REPARE con las filas marcadas"); la cola persistida sigue siendo un ticket aparte.

# Puntos abiertos (de la sesión)

* Con Excel adjunto no se atiende lo que pide el texto.
* Las dos respuestas del bot (aviso de revisión y cambios) llegan al buzón REPARE (`host_email`), como todas las de hoy.

Cerrados en `2358cd5` y `4292106`: fila inexistente (ahora va a revisión), cancelar fila ya CANCELLED (idempotente) y alta desde texto (ahora a revisión).

# Fuera de lo asignado

La sesión tocó `tests/unit_repository/test_db_postgre_core.py` (3 entradas en `METODOS`, porque la prueba fija la lista de métodos públicos).

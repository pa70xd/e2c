---
type: Module
title: Revisión por hilo (review/)
description: Aplica en cooler_request los cambios pedidos en un hilo (solo filas PENDING) y manda a revisión humana, por correo a REPARE, todo lo demás. Rama claude/e2c-revision, sin mergear.
tags: [classifier, review, hilo, fase-3]
---

# Estado

Rama `claude/e2c-revision` (commit `e872203`), parte de `claude/e2c-classifier-core`, **sin mergear**. Verificado en la rama: existen `review/{contexto,aplicador,canal}.py`, los tres SQL nuevos, `get_cooler_rows`, `update_pending_cooler_row`, `cancel_pending_cooler_row` en `repository/core/consultas_postgre.py` (`DBPostgreBase`) y los mensajes `msj_revision_repare` y `msj_cambios_hilo`. `python -m pytest -q` → **492 passed, 48 skipped, 1 xfailed**. Los 48 skip son los tests contra PostgreSQL local; **no los ejecuté**. La sesión reporta 540 passed con `E2C_TEST_PG_DSN` local.

# Cuándo actúa

`review` solo atiende un mensaje si se cumple **todo** esto (según la sesión):

* `CLASSIFIER_EXTRACT` es distinto de `regex`. **Con el default `regex` no se consulta el hilo y nada de esto corre** (los goldens no cambian).
* Dirección inbound, sin adjuntos (con Excel decide el parser, como hoy), `request_code` resuelto (sale de `email_reply_validate`, por hilo) y etapa `reply`.
* Tipo de evento `agregar_filas`, `modificar_filas`, `cancelar_filas` o `cancelar_solicitud`, y hay filas que aplicar o revisar.

# Piezas

* `contexto.py`: `cargador(repo)` lee las filas de `cooler_request` por `request_code`, sin PII. Se registra al importar `service` (resuelve el hueco 1 de [núcleo](core.md)).
* `aplicador.py`: `aplicar(decision, ctx, repo)`.
* `canal.py`: `debe_atender` y `atender`.
* SQL: `cooler_rows_by_request.sql`; `update_pending_cooler_row.sql` (`COALESCE(NULLIF(TRIM(%s),''), col)` en folio, series, modelo, tipo de servicio y dirección); `cancel_pending_cooler_row.sql`. Los dos UPDATE filtran por `request_code` + `row_number` + `status='PENDING'` y usan `RETURNING`. Las tablas siguen a `DEBUG` (`*_qa`).
* `src/service.py`: `classifier_evaluar` devuelve `(permite, decision, ctx)`; la `Decision` viaja por la llamada, ya no se usa `ultima_decision()`.

# Reglas

* Las filas **PENDING** se modifican o cancelan fila por fila. Si el UPDATE no toca nada (carrera con un outbound), la fila va a revisión con motivo `estado_cambio`.
* **Van a revisión:** ACCEPTED, CANCELLED, REJECTED, filas inexistentes y errores del repositorio. (ACCEPTED es [decisión del usuario](../riesgos/decisiones.md); CANCELLED/REJECTED siguen [pendientes de confirmación](../riesgos/decisiones.md).)
* Agregar: `send_email_coolers` con `row_number = max + 1` y `status = PENDING`. Un alta sin serie va a revisión (`agregar_sin_serie`). Una serie ya registrada queda "sin cambios" y no genera aviso.
* `cancelar_solicitud`: cancela las PENDING; la solicitud solo se cancela si no quedó nada en revisión (primero `update_email_request`, después `cancel_email_request`).

# Canal de revisión

Se manda con `reply_mail_onl_text` en el mismo hilo: primero el aviso de revisión (`msj_revision_repare`: incluye "requiere revisión" y una tabla con fila, serie, acción y motivo) y después la respuesta (`msj_cambios_hilo`). Ambos llegan a `host_email`, el buzón REPARE del cliente, como cualquier respuesta de los parsers. Esto es la propuesta de la Fase 3 ("respuesta en el hilo a REPARE con las filas marcadas"); la cola persistida sigue siendo un ticket aparte.

# Puntos abiertos (de la sesión)

1. Si un proveedor externo refiere una fila inexistente, `classifier.validate` descarta toda la extracción y cae a regex: esas filas no se aplican, no van a revisión y nadie avisa.
2. Si llega de nuevo el pedido de cancelar una fila ya CANCELLED, vuelve a avisar a REPARE (regla estricta).
3. Un alta desde texto crea una fila mínima, sin geocodificación ni distribuidora.
4. Con Excel adjunto no se atiende lo que pida el texto.

# Fuera de lo asignado

La sesión tocó `tests/unit_repository/test_db_postgre_core.py` (3 entradas en `METODOS`, porque la prueba fija la lista de métodos públicos).

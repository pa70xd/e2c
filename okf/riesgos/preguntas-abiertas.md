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
# Clasificador y revisión por hilo (Fase 3)

* Con Excel adjunto no se atiende lo que pida el texto del correo. ¿Debe atenderse?
* ¿Confirmas que las filas CANCELLED y REJECTED también van a revisión (hoy decisión de la sesión classifier-core, no tuya)?
* ¿La cola de revisión debe persistirse? Hoy solo hay correo a REPARE. Ver [revisión](../classifier/revision.md).
* Alta desde texto sin Excel: hoy va a revisión (decisión de la orquestadora). ¿Lo confirmas?

# Imbera y Torrey (Fase 4, negocio)

La orquestadora los lleva al usuario; la sesión no inventó nada. Archivos: `config/customers/imbera/reglas_imbera.py` y `config/customers/torrey/reglas_torrey.py`.

Imbera:

1. ¿Cómo se nombra al sub-cliente en la base? Hoy va a `cooler_request.cbu` tal como viene en el asunto o el cuerpo; solo se reconocen JUMEX, PISA y ELECTROLIT. Sin catálogo no se separa el cliente de la plaza en "SOLICITUD DE OS PARA <distribuidor> <plaza>".
2. ¿Cuál es el criterio exacto de garantía? Hoy cualquier señal la marca: la palabra en el asunto, un PDF adjunto (cualquier PDF cuenta como factura), la foto de la placa (solo se reconoce por el nombre del archivo), un equipo nuevo dañado o el buzón de garantías. La validación es de la etapa 2.
3. ¿Qué clientes son institucionales? La lista está vacía, así que la instalación no se restringe.
4. ¿Cuál es el formato de la OS de REPARE para Imbera y Torrey (¿prefijo 403 como Danone?)? Hoy cualquier OS concilia la fila como ACCEPTED.
5. Los seguimientos y las consultas de estatus sin Excel se ignoran y no se responden. ¿Debe responderse?

Torrey:

6. ¿La falta de factura PDF debe rechazar la solicitud? Hoy solo se avisa en la respuesta.
7. Las máquinas de hielo quedan con `cooler_request.cliente = IMBERA` dentro del `email_request` de Torrey. ¿Deben ir en un `email_request` aparte con customer imbera?
8. Falta un catálogo de modelos de máquinas de hielo; hoy solo se detectan por el texto ("máquina/fábrica de hielo", "ice maker").

# KOF (Fase 4, negocio)

1. Sufijo "R" de reubicaciones: no se sabe si KOF ya lo manda en la serie o si REPARE lo agrega, ni si se quita para conciliar. Hoy la serie se guarda tal como llega.
2. ID de servicio de "áreas generales" (proyectos especiales): falta el código. La sábana de ruta no tiene `Id_Servicio`; hoy va el texto "AREAS GENERALES" en Observaciones.
3. Nombres exactos de las columnas de la bitácora (Folio (.Net), Tipo de Movimiento, serie/modelo/SAP a instalar y a retirar). Los fixtures se armaron con la estructura descrita, no con archivos reales; con el primer correo real hay que ajustar los alias.
4. Formato real de "RE: BITACORA" con OS: se asumió la respuesta ya desdoblada (9 filas); también funciona con una sola OS por Cambio de Equipo, que concilia la instalación y el retiro.
5. Claves del correo en texto plano (proyectos especiales): hoy se aceptan líneas "CLAVE: valor" con los mismos alias y se exige el folio.
6. Regla de OS en KOF: ¿una OS vacía debe marcar REJECTED? Hoy rige la regla común: vacía REJECTED, 403 ACCEPTED, el resto PENDING.
7. Prioridad HIGH y CBU "KOF": copiados del patrón, sin confirmar con negocio.
8. Los ~10 formatos de KOF: solo están cubiertos el reporte por falla, la bitácora, su respuesta y el texto plano; los demás requieren alias nuevos.
9. Activar la suscripción de Graph del buzón y habilitar `kof` en `E2C_CLIENTES_HABILITADOS` en producción.

# Respondidas

Ver también [decisiones](decisiones.md).

* **¿Un hilo puede cancelar filas ya ACCEPTED (con OS)?** No automáticamente. Decisión del usuario del 2026-10-25, relayada por la orquestadora: va a revisión humana, igual que las correcciones sobre filas ACCEPTED. Las filas PENDING sí se pueden cancelar desde un hilo. Pendiente para la Fase 3: el canal de revisión (propuesta: respuesta en el hilo a REPARE con las filas marcadas); la cola persistida queda como ticket aparte. No implementado: hoy `bot.cancelar` actúa sobre coolers PENDING y la solicitud; no verifiqué cómo trata filas ACCEPTED.
* **¿Una corrección por hilo puede modificar filas ACCEPTED?** No. Decisión del usuario del 2026-10-25, relayada por la orquestadora: la corrección sobre una fila ya ACCEPTED no se aplica y va a revisión humana con el comentario "requiere revisión". Hoy se implementa solo como un `print` `[BASEDATOS]` en `insert_update_cooler` (rama `claude/e2c-fix-returning`, mergeada en la base). Pendiente: ese aviso vive únicamente en los logs y no hay cola de revisión persistida; queda como ticket de la Fase 3.
* ¿Se elimina el historial de `email.json` y demás datos reales?
* ¿Se cambia el webhook a validación por `clientState`?

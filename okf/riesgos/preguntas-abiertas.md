---
type: Open Questions
title: Preguntas abiertas
description: Decisiones de negocio o técnicas pendientes, agrupadas por cliente o tema, con quién debería responderlas (propuesta de okf, no asignación confirmada).
tags: [pendientes, negocio]
---

Responsables propuestos: **REPARE operación** (reglas del negocio y de los buzones), **catálogo** (quien mantiene `danone_model_line_cat.json`, distribuidoras y modelos), **dev** (decisión técnica del equipo), **usuario** (decisión de riesgo o alcance). Ver también [decisiones](decisiones.md).

# Transversales (usuario)

* ¿Confirmas que las filas CANCELLED y REJECTED también van a revisión? (hoy decisión de la sesión classifier-core, no tuya.) **Usuario.**
* Alta desde texto sin Excel: hoy va a revisión (decisión de la orquestadora). ¿Lo confirmas? **Usuario.**
* Con Excel adjunto no se atiende lo que pida el texto del correo. ¿Debe atenderse? **Usuario.**
* ¿La cola de revisión debe persistirse? Hoy solo hay correo a REPARE ([revisión](../classifier/revision.md)). **Usuario / dev.**
* `redact-v2` está mergeado y `REDACT_VERSION = 2` abre el candado, pero **quedan 2 nombres de 21 correos reales sin redactar** ([redact](../classifier/redact.md)). ¿Aceptas esa fuga residual antes de mandar correos reales a un proveedor externo (sombra/haiku)? **Usuario.**
* ¿Se elimina el historial de git de `email.json` y demás datos reales (también las direcciones personales que ya se quitaron del árbol)? **Usuario / dev.**
* ¿Se cambia el webhook a validación por `clientState` (y `subscriptions.py` que aún no lo envía)? **Dev.**
* `EMAIL_SENDER` (`infrastructure/graphapi/graphapi.py:44`) y el default de `MAIL` (`src/handler.py:26`) tienen una dirección hardcodeada. ¿Se mueven a una `MAIL` obligatoria? **Dev.**

# KOF (parser mergeado, apagado por defecto)

1. Sufijo "R" de reubicaciones: no se sabe si KOF ya lo manda en la serie o si REPARE lo agrega, ni si se quita para conciliar. Hoy la serie se guarda tal como llega. **REPARE operación.**
2. ID de servicio de "áreas generales" (proyectos especiales): falta el código; hoy va el texto "AREAS GENERALES" en Observaciones. **REPARE operación.**
3. Nombres exactos de las columnas de la bitácora (Folio (.Net), Tipo de Movimiento, serie/modelo/SAP a instalar y a retirar). Los fixtures no vienen de archivos reales; con el primer correo real hay que ajustar los alias. **REPARE operación + dev.**
4. Formato real de "RE: BITACORA" con OS (se asumió la respuesta ya desdoblada, 9 filas). **REPARE operación.**
5. Claves del correo en texto plano (proyectos especiales): hoy "CLAVE: valor" con los mismos alias y se exige el folio. **REPARE operación.**
6. ¿Una OS vacía debe marcar REJECTED en KOF? Hoy rige la regla común (vacía REJECTED, 403 ACCEPTED, el resto PENDING). **REPARE operación.**
7. Prioridad HIGH y CBU "KOF": copiados del patrón, sin confirmar. **REPARE operación.**
8. Los ~10 formatos de KOF: solo están cubiertos el reporte por falla, la bitácora, su respuesta y el texto plano. **REPARE operación + dev.**
9. Activar la suscripción de Graph del buzón y habilitar `kof` en `E2C_CLIENTES_HABILITADOS` en producción. **Dev, después de 1-8.**

# Imbera y Torrey (parsers mergeados, apagados por defecto)

Archivos: `config/customers/imbera/reglas_imbera.py` y `config/customers/torrey/reglas_torrey.py`. La sesión no inventó nada.

Imbera:

1. ¿Cómo se nombra al sub-cliente en la base? Hoy va a `cooler_request.cbu` tal como viene; solo se reconocen JUMEX, PISA y ELECTROLIT. Sin catálogo no se separa el cliente de la plaza en "SOLICITUD DE OS PARA <distribuidor> <plaza>". **Catálogo + REPARE operación.**
2. ¿Cuál es el criterio exacto de garantía? Hoy cualquier señal la marca (palabra en el asunto, cualquier PDF como factura, foto de la placa solo por nombre de archivo, equipo nuevo dañado, buzón de garantías). La validación es de la etapa 2. **REPARE operación.**
3. ¿Qué clientes son institucionales? La lista está vacía, así que la instalación no se restringe. **REPARE operación.**
4. ¿Cuál es el formato de la OS de REPARE para Imbera y Torrey (¿prefijo 403 como Danone?)? Hoy cualquier OS concilia la fila como ACCEPTED. **REPARE operación.**
5. Los seguimientos y las consultas de estatus sin Excel se ignoran y no se responden. ¿Debe responderse? **REPARE operación.**

Torrey:

6. ¿La falta de factura PDF debe rechazar la solicitud? Hoy solo se avisa en la respuesta. **REPARE operación.**
7. Las máquinas de hielo quedan con `cooler_request.cliente = IMBERA` dentro del `email_request` de Torrey. ¿Deben ir en un `email_request` aparte? **REPARE operación + dev.**
8. Falta un catálogo de modelos de máquinas de hielo. **Catálogo.**

# Oxxo (parser mergeado, apagado por defecto)

1. **Riesgo de duplicado con la PoC externa:** ¿quién lleva la PoC y cuándo se apaga para encender `oxxo`/`oxxo_garantias` sin duplicar OS? El corte lo decide REPARE. **REPARE operación.**
2. Las OS entran sin CP, coordenadas, distribuidora ni pre-sábana; sábanas y Tableau no las ven completas. ¿Se acepta o se enriquece después? **REPARE operación + dev.**
3. Plaza vacía: la plantilla junta "<plaza> <nombre tienda>" sin delimitador. ¿Cuál es el formato real? **REPARE operación (con Oxxo).**
4. El outbound REPARE → Oxxo no se concilia. ¿Debe conciliarse? **REPARE operación.**
5. Carrera residual que puede dejar un `email_request` huérfano. ¿Se cubre? **Dev.**
6. `oxogar` → `oxxo_garantias` no se nombró en el alcance aprobado el 2026-10-26. ¿Lo confirmas? **Usuario.**

# Danone, Penafiel y catálogo de modelos

* **46 de 803 modelos únicos del catálogo son ambiguos** y salen vacíos con motivo `ambiguo` ([lista](../pruebas/evaluacion.md) en `eval/reportes/modelos_ambiguos.md`). **Catálogo.**
* Penafiel usa el catálogo de Danone (no tiene propio): ¿es correcto? **Catálogo + REPARE operación.**
* Cómo llevar a REPARE el motivo del modelo no resuelto (hoy un párrafo en el correo de respuesta). **REPARE operación + dev.**
* ¿Por qué `TRASLADO` no está en Danone? Penafiel sí lo incluye. **REPARE operación.**
* ¿Modelo, línea y categoría entran para equipos de competencia? La decisión de integrar el CRM no está tomada. **REPARE operación.**

# Holanda

* ¿Confirmar modelo sin catálogo ("CONFIRMAR MODELO")? **Catálogo + REPARE operación.**
* ¿Quién es el responsable de remitentes autorizados? La lista está vacía con TODO. **REPARE operación.**
* ¿MERMA se debe leer en outbound? Hoy no. **REPARE operación.**
* ¿CASO2 se reutiliza o se corrige? **REPARE operación.**

# Heineken

* ¿Canal D2D a CBU: qué mapeo es el correcto? **REPARE operación.**
* Si `NUMERO CASO` o `FOLIO` llega lleno, ¿va a Folio u Orden? **REPARE operación.**
* Cambios (`RETIRO POR CAMBIO`, `CAMBIO DE ENF`): ¿debe generar también la entrega del equipo de reemplazo? **REPARE operación.**

# Respondidas

Ver también [decisiones](decisiones.md).

* **¿Un hilo puede cancelar filas ya ACCEPTED (con OS)?** No automáticamente. Decisión del usuario del 2026-10-25, relayada por la orquestadora: va a revisión humana, igual que las correcciones sobre filas ACCEPTED. Las filas PENDING sí se pueden cancelar desde un hilo. Pendiente para la Fase 3: el canal de revisión (propuesta: respuesta en el hilo a REPARE con las filas marcadas); la cola persistida queda como ticket aparte. No implementado: hoy `bot.cancelar` actúa sobre coolers PENDING y la solicitud; no verifiqué cómo trata filas ACCEPTED.
* **¿Una corrección por hilo puede modificar filas ACCEPTED?** No. Decisión del usuario del 2026-10-25, relayada por la orquestadora: la corrección sobre una fila ya ACCEPTED no se aplica y va a revisión humana con el comentario "requiere revisión". Hoy se implementa solo como un `print` `[BASEDATOS]` en `insert_update_cooler` (rama `claude/e2c-fix-returning`, mergeada en la base). Pendiente: ese aviso vive únicamente en los logs y no hay cola de revisión persistida; queda como ticket de la Fase 3.
* ¿Se elimina el historial de `email.json` y demás datos reales?
* ¿Se cambia el webhook a validación por `clientState`?

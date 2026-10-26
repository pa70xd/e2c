---
type: Client Integration
title: KOF
description: Parser KOF_INIT/KOF_REPLY ("Lay Out Repare" de KOF) con ruta, movimiento y conciliación por OS. Fase 4, rama claude/e2c-kof, sin mergear. En la base sigue siendo un stub.
resource: https://github.com/pa70xd/e2c/blob/claude/admiring-lovelace-3oh7g0/parsers/kof.py
tags: [kof, fase-4]
---

# Estado

* **En la base (`claude/admiring-lovelace-3oh7g0`)**: `parsers/kof.py` sigue siendo un stub que solo imprime; no está registrado en `PARSERS_INIT`/`PARSERS_REPLY`; `customer.json` es de 0 bytes.
* **En la rama `claude/e2c-kof` (`b7f6e64` y `295dc97`; aprobada por la orquestadora, que la mergea; **no la veo aún en la base**)**: parser real. Verificado: existen `parsers/kof.py`, `parsers/kof_parse/{lector_adapter,reader,business,sabana,process_data,mensajes}.py`, `config/customers/kof/{columns_names,reglas_kof}.py` y `customer.json`, 11 goldens `kof_*` y `tests/unit_kof/`; `KOF_INIT`/`KOF_REPLY` registrados como `kof` y `test_kof` en `src/service.py`. `python -m pytest -q` en la rama → **942 passed, 1 failed, 48 skipped, 1 xfailed** (medido sobre `b7f6e64`). El fallo era `test_gate_en_parser_init_cubre_danone_y_penafiel`; según la sesión, en `295dc97` esa prueba ahora acepta un subconjunto (`<=`) de clientes sin gate en el parser y la suite da 1088 passed con 0 diff en goldens (no lo repetí sobre `295dc97`). Que los goldens existentes no cambiaron es afirmación de la sesión.
* Sigue detrás de `E2C_CLIENTES_HABILITADOS` ([despliegue](../deploy/despliegue.md)) y el buzón de KOF viene en la rama del lector (`email_index.json`, mergeada).

# Flujo (según la sesión)

Por hilo, igual que Danone y Penafiel.

* **INIT** con Excel: todas las hojas, **también las ocultas**; el encabezado se busca en las primeras 15 filas; filas con menos de 2 celdas son basura; las filas repetidas entre hojas se descartan. O texto plano "CLAVE: valor" con folio (→ PROYECTO ESPECIAL).
* **REPLY** inbound agrega filas tras el último `row_number`; outbound concilia por serie con la columna OS (regla 403 común); `reply_to_bot` usa `bot/commands.py`.
* Gate del clasificador: se aplica en `service` (no está en `GATE_EN_PARSER_INIT`).
* **Lector común** (desde `295dc97`, verificado en `lector_adapter.py`): `leer_adjunto(hojas_ocultas="si_coinciden", vocabulario = alias de config/customers/kof/columns_names.py, claves = serie, folio, falla y tipo de movimiento, min_coincidencias=3)`. La descarga por Graph y el Base64 siguen en el adaptador. Un `AdjuntoIlegible` se registra y se salta; un Excel sin encabezado de KOF responde "formato desconocido"; un correo sin Excel ni texto plano con folio se ignora. Ver [lector](lector.md).
* **Habilitación:** el buzón de KOF ya está en `config/email_index.json` (verificado: 1 coincidencia en la rama). Además el cliente debe estar en `E2C_CLIENTES_HABILITADOS`, y la suscripción de Graph (`subscriptions.py`) **sigue comentada**: falta activarla.

# Reglas (según la sesión)

* Falla → ruta "SERVICIO DE DISTRIBUIDOR".
* Extensión, charolas o parrillas en FALLA o SOLICITUD DE SERVICIO → "VENTA DE MATERIAL" (nunca falla; OBSERVACIONES no cuenta).
* Cobertura, Equipo Adicional e Instalación → INSTALACION. Cambio de Equipo → INSTALACION + RETIRO (columnas de serie, modelo y SAP del equipo a retirar).
* Folio (.Net) → `cooler_request.folio`. Serie → `serie_fabricante`; ACTIVO/PLACA o SAP → `serie_dnn_bnf`. Distribuidora = "ID DISTRIBUIDOR | CEDIS" (KOF no trae CP).
* **Rechazos:** serie vacía, serie a retirar vacía, ID detallista vacío, tipo de movimiento no reconocido, sin tipo ni falla, serie repetida.
* **Respuesta:** sábanas más `RESULTADO_KOF_<folio>.xlsx` con aceptadas y rechazadas; **sin aceptadas no se crea folio**.
* Datos: `repository.gen` `DB_POSTGRE` (sobre `repository/core`), sin SQL nuevo. Prioridad HIGH, cbu KOF.

# Preguntas abiertas

Ver [preguntas abiertas](../riesgos/preguntas-abiertas.md): sufijo R de reubicación; código del ID de servicio "áreas generales" (hoy texto en Observaciones); nombres exactos de columnas de la bitácora y del texto plano; formato real de la respuesta con OS; si OS vacía = REJECTED en KOF; suscripción de KOF.

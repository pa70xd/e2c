---
type: Module
title: Imbera y Torrey ("Lay Out Repare")
description: Parsers de Imbera (multi-cliente) y Torrey (máquinas de hielo) para el Excel "Lay Out Repare". Fase 4, rama claude/e2c-imbera-torrey, sin mergear.
tags: [parsers, imbera, torrey, fase-4]
---

# Estado

Rama `claude/e2c-imbera-torrey` (commits `07f3fea`, `b4cb7ac` y `01bf07a`, con la base `3732c25` ya mergeada en la rama), **sin mergear**. Verificado en la rama: existen `parsers/imbera.py`, `parsers/torrey.py`, `parsers/imbera_parse/` (lector, layout, clasificación, business, sabana, process_data, conciliación, mensajes, flujo, perfil), `parsers/torrey_parse/hielo.py`, `config/customers/{imbera,torrey}/`, `repository/imbera/` (con 2 SQL de OS) y las entradas `IMBERA_INIT/REPLY` y `TORREY_INIT/REPLY` en `src/service.py`; `python -m pytest -q` → **1081 passed, 2 failed, 48 skipped, 1 xfailed** (la orquestadora aprobó la rama `01bf07a` para merge) en mi contenedor (los 2 fallos son por falta de `odfpy`; 1081 + 2 = 1083, la cifra de la sesión); hay 17 archivos golden de Imbera/Torrey (la sesión dice que son nuevos y que ninguno de los existentes cambió; no lo comparé). Ambos clientes están detrás de `E2C_CLIENTES_HABILITADOS` ([despliegue](../deploy/despliegue.md)). Ningún golden existente cambió (afirmación de la sesión).

# Lectura

* Hoja `RUTA`; variante A (una fila de encabezado) y B (fila de grupos combinados más columnas).
* Hojas ocultas: solo se leen si traen `MODELO` y `SERIE`, así que los catálogos se ignoran. La fila basura se descarta.
* Desde `01bf07a` leen con el [lector común](lector.md) (`leer_adjunto`, `hojas_ocultas="si_coinciden"`; verificado en `imbera_parse/lector.py`), así que se ignoran los catálogos ocultos `LinesByCategori` y `ModelsByLines`. Aceptan `.xlsx`, `.xls`, `.xlsm` y `.ods`.
* **Variante B:** la fila de grupos no cuenta como encabezado; las columnas se mapean por su nombre simple y, si un nombre se repite entre grupos, gana el primero.

# Reglas (según la sesión)

* **Imbera es multi-cliente:** el sub-cliente se lee del asunto o del cuerpo y va a `cbu` (TODO: cómo se nombra en la base). Los folios `IMB-`/`REP-` van a `folio`; la OS del asunto de una garantía va a `ticket_solicitud`. Hay 3 variantes de ruta (`folio_app`, `proyecto_especial`, `distribuidora`).
* **Garantía:** solo se **marca** (la etapa 2 la valida). Señales: la palabra en el asunto, un PDF, la foto de la placa (por nombre), un equipo nuevo dañado y el buzón de garantías. Torrey se marca siempre.
* **Rechazos:** serie vacía, modelo vacío, serie repetida y retiro/traslado. Las filas rechazadas se persisten como `REJECTED` con su motivo, y la respuesta lista aceptadas y rechazadas sin datos personales.
* **Outbound:** la OS se toma del Excel (por serie) o del texto ("orden generada: <n>"); esto último se puede apagar por cliente. Si la OS no se asigna a una sola fila, no se aplica (revisión). "Espera de pieza" se trata como `no_os`.
* **Torrey:** la máquina de hielo queda con cliente IMBERA y se contesta en el hilo de Torrey. Si falta la factura PDF, se avisa en la respuesta.

# Nota técnica sobre el lector común

Al iterar `Tabla.df` con `iterrows()`, una celda vacía llegó como `NaN` y no como `None` (en el `df` directo sí es `None`). El adaptador de Imbera lo cubre; el tema está asignado a la sesión del lector (sin confirmar corrección). Ver [lector](lector.md).

# Pendientes

* Los buzones de Imbera y Torrey ya están en `config/email_index.json` de esta rama (heredados del lector, ya en la base). Apagados por defecto: se encienden con `E2C_CLIENTES_HABILITADOS="imbera,torrey"`.
* **TODO de negocio** (ver [preguntas abiertas](../riesgos/preguntas-abiertas.md)): nombre del sub-cliente en la base, criterio exacto de garantía, lista de clientes institucionales, formato de la OS (¿403?), si sin factura se rechaza en Torrey, si el hielo va en un `email_request` aparte y el catálogo de modelos de hielo.

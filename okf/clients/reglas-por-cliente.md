---
type: Business Rules
title: Reglas de negocio por cliente
description: Reglas más importantes por cliente, con referencias a los archivos que las definen. No es exhaustivo.
tags: [reglas, negocio]
---

# Danone

* Archivos: `config/customers/danone/` (`columns_names.py`, `datos_esenciales_solicitud.py`, `movimientos_danone.py`, `model_line_cat.py`).
* CBU determina cadena: ONE DANONE, DANONE, EDP, ONE COOLER → DANONE; BONAFONT, BNF → BONAFONT.
* Tipo de servicio válido: solo los de `DIC_SABANAS_MOV` (MOVIMIENTOS y RUTA).
* Prioridad HIGH.
* Catálogo de modelos: 851 modelos en 41 pares categoría/línea. Un modelo puede estar en varias listas; gana la primera en orden de dict. Hay un placeholder `'XXXXX'`.

# Penafiel

* Archivos: `config/customers/penafiel/`.
* CBU fijo `PENAFIEL`. Claves de CBU con variantes (penafiel, penañafiel, peñafiel). La ñ no funciona en la búsqueda.
* Sin dedupe de equipos.

# Holanda

* Asunto válido: `casos repare`; en la rama `claude/e2c-fix-holanda-indice` (mergeada en la base) también con fecha o sufijo numérico.
* Origen por sufijo de CASO2: `H` → HELADIO, `G` → GDR. Otro origen rechaza la fila.
* Canal fijo `SC | Sin Canal`.
* Marca de duplicado: `DUPLICADO`. Un equipo es duplicado mientras tenga otro caso sin OS.
* Remitentes autorizados: lista vacía con TODO.

# Heineken

* Canal → puesto: `CANAL MODERNO` → D2362, `PUNTO DE VENTA` → D2363, `CENTRO DE CONSUMO` → D2364. Región Oriente, sucursal 7203.
* Servicios D2D como tuplas posicionales de 7 campos.
* Serie genérica con prefijo `HEI` o `MOB`.
* Ver [parser](../parsers/heineken.md) para los pendientes de cambios.

# Reglas generales

* Mensajes de estado: "equipos con OS (ACEPTADOS)", "equipos sin OS (PENDIENTES)", "equipos sin OS (RECHAZADOS)".
* Comandos reservados: `bot.help`, `bot.ayuda`, `bot.estatus`, `bot.status`, `bot.cancelar`, `bot.finalizar`, `bot.cerrar`, `bot.global`.

# Dónde se encuentran los datos de referencia

Ver [catálogos](../data/catalogos.md).

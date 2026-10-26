---
type: Module
title: Lector común de adjuntos (parsers/core/lector.py)
description: Lector único de Excel/ODS por vocabulario de encabezados, con manejo de hojas ocultas y filas basura. Fase 4, rama claude/e2c-lector-excel, sin mergear.
tags: [parsers, lector, excel, fase-4]
---

# Estado

Rama `claude/e2c-lector-excel` (commits `b3e308e` y `717cb96`), **sin mergear**. Verificado en la rama: existe `parsers/core/lector.py` y `odfpy==1.4.1` está en `requirements.txt`. `python -m pytest -q` en la rama → **922 passed, 2 failed, 48 skipped, 1 xfailed** en este contenedor; los 2 fallos son `ModuleNotFoundError: No module named 'odf'` porque no pude instalar `odfpy==1.4.1` aquí (falla al construir la rueda). La sesión reporta 924 passed, 48 skipped, 1 xfailed con la dependencia instalada, lo cual es coherente (922 + 2). Los goldens sin diff es afirmación de la sesión.

# API

`leer_adjunto(nombre, bytes, vocabulario, hojas_ocultas="si_coinciden"|"nunca"|"siempre", *, claves=(), min_coincidencias=2) -> list[Tabla(archivo, hoja, oculta, fila_encabezado, columnas, df, descartes)]`.

* **Formatos:** `.xlsx`, `.xls`, `.xlsm`, `.ods`. Ojo: `.xls` necesita `xlrd`, que **no está en `requirements.txt`** (verificado: solo aparece `odfpy`).
* **Encabezado por vocabulario, no por posición:** busca coincidencias en las primeras 15 filas; los encabezados se normalizan (mayúsculas, sin acentos, saltos de línea y espacios alrededor de "/" colapsados). Resuelve los encabezados de Imbera de 2 a 4 filas ([correos reales](../pruebas/correos-reales.md)).
* **Hojas ocultas:** `si_coinciden` lee la oculta solo si sus columnas son las de una hoja visible de datos (caso KOF); los catálogos ocultos de Imbera/Torrey se ignoran.
* **Filas basura** (vacías, de una celda, sin clave, encabezado repetido): se descartan y se cuentan en `Tabla.descartes`, con log `[LECTOR]` sin valores.
* Archivo ilegible → `AdjuntoIlegible` (`ValueError`); extensión no soportada → `ValueError`.
* Pruebas con archivos sintéticos: `tests/fixtures/lector/build_lector_fixtures.py` y `tests/unit_core/test_lector.py` (21).

# Lo que NO se migró

Los lectores actuales (Danone, Penafiel, Holanda, Heineken, `gen_parse`) **no usan** el lector común todavía; solo se les agregó `.xlsm` y `.ods` a sus extensiones. Esto cierra el `.xlsm` de Holanda y Danone, pero **una `.ods` en esos lectores no filtra hojas ocultas** (lo hará la migración). Ver [bugs](../riesgos/bugs.md).

# Clientes nuevos y flag

Ver [clientes](../clients/index.md) y [decisiones](../riesgos/decisiones.md). El flag `E2C_CLIENTES_HABILITADOS` y los buzones nuevos van en la misma rama (`717cb96`).

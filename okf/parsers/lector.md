---
type: Module
title: Lector común de adjuntos (parsers/core/lector.py)
description: Lector único de Excel/ODS por vocabulario de encabezados, con manejo de hojas ocultas y filas basura. Fase 4, mergeado en la base (claude/e2c-lector-excel).
tags: [parsers, lector, excel, fase-4]
---

# Estado

Rama `claude/e2c-lector-excel` (commits `b3e308e`, `717cb96`, `b0758f7`, `41eafbf`), **mergeada en la base** (`3732c25`). Verificado en la rama: existe `parsers/core/lector.py` y `odfpy==1.4.1` está en `requirements.txt`. `python -m pytest -q` en la rama → **922 passed, 2 failed, 48 skipped, 1 xfailed** en este contenedor; los 2 fallos son `ModuleNotFoundError: No module named 'odf'` porque no pude instalar `odfpy==1.4.1` aquí (falla al construir la rueda). La sesión reporta, con la dependencia instalada y tras los commits finales, 928 passed, 48 skipped, 1 xfailed (no lo repetí tras `41eafbf`). Los goldens sin diff es afirmación de la sesión.

# API

`leer_adjunto(nombre, bytes, vocabulario, hojas_ocultas="si_coinciden"|"nunca"|"siempre", *, claves=(), min_coincidencias=2) -> list[Tabla(archivo, hoja, oculta, fila_encabezado, columnas, df, descartes)]`.

* **Formatos:** `.xlsx`, `.xls`, `.xlsm`, `.ods`. También Base64. `xlrd==2.0.2` quedó en `requirements.txt` y `xlwt==1.3.0` solo en `requirements-dev.txt` (verificado en la rama; para el fixture de `.xls`).
* **Encabezado por vocabulario, no por posición:** busca coincidencias en las primeras 15 filas; los encabezados se normalizan (mayúsculas, sin acentos, saltos de línea y espacios alrededor de "/" colapsados). Resuelve los encabezados de Imbera de 2 a 4 filas ([correos reales](../pruebas/correos-reales.md)).
* **Hojas ocultas:** `si_coinciden` lee la oculta solo si sus columnas son las de una hoja visible de datos (caso KOF); los catálogos ocultos de Imbera/Torrey se ignoran.
* **Filas basura** (vacías, de una celda, sin clave, encabezado repetido): se descartan y se cuentan en `Tabla.descartes`, con log `[LECTOR]` sin valores.
* Archivo ilegible → `AdjuntoIlegible` (`ValueError`); extensión no soportada → `ValueError`.
* Pruebas con archivos sintéticos: `tests/fixtures/lector/build_lector_fixtures.py` y `tests/unit_core/test_lector.py` (21).

# Bugs de `.xls` encontrados y corregidos en la rama

1. `.xls` figuraba en las listas de extensiones pero `xlrd` no estaba en `requirements.txt`: **nunca abrió un `.xls`**. Corregido con `xlrd==2.0.2` (`b0758f7`).
2. `parsers/danone_parse/reader.py` y `parsers/gen_parse/reader.py` (este último lo usa Penafiel) usaban `book.sheet_visibility`, que no existe en xlrd 2.x (`AttributeError`). Ahora usan `sheet.visibility == 0` (`41eafbf`; verificado en la rama). Holanda y Heineken no estaban afectados (según la sesión).

# Pendiente: build de `odfpy` con Python 3.14

`odfpy==1.4.1` (nuevo en `requirements.txt`, solo sdist) instaló limpio, según la sesión, en un venv nuevo con Python 3.13 (`pip install --no-cache-dir -r requirements.txt`), pero **no se probó con Python 3.14**, que es la imagen del Dockerfile: **falta verificar el build de la imagen**. En mi contenedor (Python 3.13, `pip` como root, sin venv) la instalación de `odfpy==1.4.1` falló al construir la rueda, así que el riesgo es real y depende del entorno de instalación.

# Celdas vacías: `None`, no `NaN` (rama `claude/e2c-lector-nan`, sin mergear)

Commits `ba62b70` y `b499447`; aprobada y en merge (no confirmado en la base). Verificado en la rama: existen `DataFrameLector`, `Tabla.filas()` y `_sin_nan`; `pytest -q` → 936 passed, 2 failed (falta `odfpy`), 48 skipped, 1 xfailed (936 + 2 = 938, la cifra de la sesión).

* **Bug (según la sesión):** con pandas 3.x, `DataFrame.iterrows()` reconstruye cada fila como `Series` y, al inferir el dtype `str` por defecto, los `None` de un DataFrame `object` pasan a `NaN`. `itertuples`, `to_dict("records")`, `iloc` y `values.tolist()` conservan `None`. Un `NaN` que llega a PostgreSQL se guarda como `'NaN'` o falla. Mi contenedor tiene pandas 3.0.3; en una prueba con un DataFrame `object` explícito `iterrows()` devolvió `None`, lo que concuerda con que el problema depende del dtype inferido.
* **Corrección 1:** `Tabla.df` es ahora un `DataFrameLector` (subclase de `DataFrame`) cuyo `iterrows` fuerza dtype `object`. Nuevo `Tabla.filas() -> list[dict]` con `None` y la fila de la hoja en `_fila`. Si alguien envuelve el `df` con `pd.DataFrame(...)` o lo concatena, pierde la subclase y vuelve el comportamiento de pandas.
* **Corrección 2 (red de seguridad central):** en `infrastructure/database/postgres.py`, `execute_query` aplica `_sin_nan(params)` antes de ejecutar: convierte `NaN` (también `np.float32/64`), `pd.NA` y `pd.NaT` en `None`, recorriendo tuplas, listas y dicts anidados. `str`, `bytes`, `Json`, fechas, `Decimal`, `inf` y el texto "nan" pasan intactos. Ver [PostgreSQL](../infrastructure/postgres.md).
* **Sitios con `iterrows` que siguen sin arreglar** (ninguno manda `NaN` directo a PostgreSQL, hoy cubiertos por la red): `parsers/{danone,penafiel,gen}_parse/process_data.py` (arman `detalles` por cooler; los más expuestos), `parsers/{danone,gen}_parse/catalog.py` (escriben a DuckDB), los `UPDATE` de `MODELO_GEN` en DuckDB (ya usan `pd.isna`) y `repository/core/consultas_postgre.py:549` (`update_cooler`, el caso real que queda protegido).
* **Regla para migrar lectores viejos al lector común:** iterar con `itertuples`, `to_dict` o `filas()` en lugar de `iterrows` sobre DataFrames ajenos.

# Lo que NO se migró

Los lectores actuales (Danone, Penafiel, Holanda, Heineken, `gen_parse`) **no usan** el lector común todavía; solo se les agregó `.xlsm` y `.ods` a sus extensiones. Esto cierra el `.xlsm` de Holanda y Danone, pero **una `.ods` en esos lectores no filtra hojas ocultas** (lo hará la migración). Ver [bugs](../riesgos/bugs.md).

# Clientes nuevos y flag

Ver [clientes](../clients/index.md) y [decisiones](../riesgos/decisiones.md). El flag `E2C_CLIENTES_HABILITADOS` y los buzones nuevos van en la misma rama (`717cb96`).

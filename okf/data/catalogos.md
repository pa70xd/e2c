---
type: Data Catalog
title: Catálogos y archivos de datos
description: Catálogos en código y archivos de datos del repo, con su uso y sus problemas.
tags: [catalogos, datos]
---

# En código

| Archivo | Contenido | Uso | Problemas |
|---|---|---|---|
| `config/config_general/distribuidoras.py` | `CATALOG_DISTRIBUIDORAS`: 3,471 entradas `código \| nombre`. En la rama `claude/e2c-catalogos` (Fase 2, mergeada) los datos viven en `config/data/distribuidoras.json` y el `.py` solo los carga. | Danone (`catalog.py`) | Nombres truncados (~50 con paréntesis sin cerrar). Clave `502635` duplicada (colapsada al último valor). |
| `config/customers/danone/model_line_cat.py` | 851 modelos, 20 categorías, 41 pares. Desde la Fase 2 (rama `claude/e2c-catalogos`, mergeada) los datos viven en `config/data/danone_model_line_cat.json` | Danone (`catalog.py`) | Un modelo en varias listas. Placeholder `XXXXX`. Copia de CH en CONGELADOR y CORTINA. |
| `config/customers/heineken/reglas_heineken.py` | Canal, puesto, distribuidora, servicios D2D | Heineken | Tuplas posicionales. Distribuidora fija. |
| `config/config_general/compact_names.py` | Nombre corto de distribuidora | Sin uso activo | Lanza ValueError si se activa para Penafiel. |

## Cargador de JSON (rama `claude/e2c-catalogos`, mergeada en la base)

* `config/data/loader.py::load_json(name)` lee `config/data/<name>` en UTF-8 y devuelve el objeto JSON. La ruta se resuelve con `Path(__file__)`, no con el cwd.
* Mismos nombres, tipos, valores y orden que antes (`CATALOG_DISTRIBUIDORAS` dict `str→str`; `catalog` dict categoría → dict → lista). Los problemas de datos siguen igual (nombres truncados, clave duplicada, placeholder `XXXXX`).
* Editar estos catálogos ahora significa editar el JSON.
* `tests/unit_catalogos/` compara contra el original del commit `55acb2f`.
* Verificado en la rama antes del merge: 3471 / 20 / 41 / 851 y `pytest -q` → 310 passed, 24 skipped, 1 xfailed.

# Archivos de datos en raíz

| Archivo | Contenido | Nota |
|---|---|---|
| `model_serie.csv` | 14 filas, serie a modelo | Datos de prueba |
| `model_activo.csv` | 1 fila | Subconjunto de model_serie |
| `dfs_pto_venta.csv` | 19 puntos de venta | 7 filas con caracteres corruptos (U+FFFD) |
| `tabla_con_distribuidora.csv` | 8 filas de solicitud | Contiene teléfonos, direcciones y coordenadas reales |
| `solicitudes_rechazadas.csv` | 8 filas de rechazadas | Encabezado con typo `FECHA SOLCITUD`. No coincide con el SQL. |
| `email.json` | Volcado de un mensaje Graph | Ya no está en el índice (mergeado en `claude/admiring-lovelace-3oh7g0`, rama `claude/e2c-fix-mecanicos`); sigue en el historial. Contiene datos personales de terceros. Ver [seguridad](../riesgos/seguridad.md). |
| `email_model.json` | Ejemplo de `email_request` | Incluye cuerpo de correo real. Ya no está en el índice (rama `claude/e2c-fix-mecanicos`, mergeada). |
| `mail.json` | Volcado `__dict__` de kiota | No es JSON válido de Graph. Ya no está en el índice (rama `claude/e2c-fix-mecanicos`, mergeada). |
| `emails pruebas` | Archivo vacío | Sin uso |

# Excel de plantilla

`excel_templates/`: `solicitud.xlsx`, `template_movimientos.xlsx`, `template_rutas.xlsx`, `template_rechazadas.xlsx`. Usados por [excel_ingestion](../services/excel-ingestion.md).

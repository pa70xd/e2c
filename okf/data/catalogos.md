---
type: Data Catalog
title: Catálogos y archivos de datos
description: Catálogos en código y archivos de datos del repo, con su uso y sus problemas.
tags: [catalogos, datos]
---

# En código

| Archivo | Contenido | Uso | Problemas |
|---|---|---|---|
| `config/config_general/distribuidoras.py` | ~3,472 entradas `código \| nombre` | Danone (`catalog.py`) | Nombres truncados (~50 con paréntesis sin cerrar). Clave `502635` duplicada. |
| `config/customers/danone/model_line_cat.py` | ~851 modelos, 20 categorías, 41 pares | Danone (`catalog.py`) | Un modelo en varias listas. Placeholder `XXXXX`. Copia de CH en CONGELADOR y CORTINA. |
| `config/customers/heineken/reglas_heineken.py` | Canal, puesto, distribuidora, servicios D2D | Heineken | Tuplas posicionales. Distribuidora fija. |
| `config/config_general/compact_names.py` | Nombre corto de distribuidora | Sin uso activo | Lanza ValueError si se activa para Penafiel. |

# Archivos de datos en raíz

| Archivo | Contenido | Nota |
|---|---|---|
| `model_serie.csv` | 14 filas, serie a modelo | Datos de prueba |
| `model_activo.csv` | 1 fila | Subconjunto de model_serie |
| `dfs_pto_venta.csv` | 19 puntos de venta | 7 filas con caracteres corruptos (U+FFFD) |
| `tabla_con_distribuidora.csv` | 8 filas de solicitud | Contiene teléfonos, direcciones y coordenadas reales |
| `solicitudes_rechazadas.csv` | 8 filas de rechazadas | Encabezado con typo `FECHA SOLCITUD`. No coincide con el SQL. |
| `email.json` | Volcado de un mensaje Graph | Versionado en la base; mergeado en `claude/admiring-lovelace-3oh7g0` (rama `claude/e2c-fix-mecanicos`) se quita del índice. Contiene datos personales de terceros. Ver [seguridad](../riesgos/seguridad.md). |
| `email_model.json` | Ejemplo de `email_request` | Incluye cuerpo de correo real. En rama `claude/e2c-fix-mecanicos` se quita del índice. |
| `mail.json` | Volcado `__dict__` de kiota | No es JSON válido de Graph. En rama `claude/e2c-fix-mecanicos` se quita del índice. |
| `emails pruebas` | Archivo vacío | Sin uso |

# Excel de plantilla

`excel_templates/`: `solicitud.xlsx`, `template_movimientos.xlsx`, `template_rutas.xlsx`, `template_rechazadas.xlsx`. Usados por [excel_ingestion](../services/excel-ingestion.md).

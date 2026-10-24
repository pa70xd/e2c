---
type: Module
title: excel_ingestion
description: Llenado de plantillas Excel de respuesta y restauración de validaciones x14.
resource: https://github.com/pa70xd/e2c/blob/claude/admiring-lovelace-3oh7g0/src/excel_ingestion.py
tags: [excel, plantillas]
---

# Uso activo

* `get_excelv2_attachment`: rellena la plantilla correspondiente desde las sábanas y devuelve los bytes. Lo usan Danone, Holanda, Penafiel y Heineken.
* `restore_x14_validations`: restaura validaciones de datos x14 que openpyxl pierde al guardar.
* Mapa de plantillas en `excel_templates/`: `solicitud.xlsx`, `template_movimientos.xlsx`, `template_rutas.xlsx`, `template_rechazadas.xlsx`.

# Variables

* `PROJECT_ID`, `REPARE_BUCKET`.

# Sin uso

* `extract_excel`, `extract_and_load`, `get_excel_attachment`.

# Problemas

* Ruta Windows `C:\keys\...json` con clave de cuenta de servicio en disco local. No existe en Cloud Run. Está en la línea 25. Ver [seguridad](../riesgos/seguridad.md).
* `extract_and_load` usa esa clave pero la subida a bucket está comentada.
* SQL armado con f-string en la línea 213.
* Lee la plantilla dos veces (líneas 234-237).

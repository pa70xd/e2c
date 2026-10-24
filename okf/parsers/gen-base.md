---
type: Module
title: Base compartida gen_parse
description: Librería base de parsers. Penafiel la usa completa; Danone solo usa la descarga de adjuntos.
resource: https://github.com/pa70xd/e2c/blob/claude/admiring-lovelace-3oh7g0/parsers/gen_parse/
tags: [parsers, base]
---

# Qué contiene

* `reader.py`: `get_adjuntos` (acepta `.xlsm`), `download_original_files`, `detectar_tipo_correo`.
* `utils.py`: `analizar_proposito`, `unir_tablas`, `mark_rejected_original_files` por SERIE, normalización de texto.
* `catalog.py`: `calcula_distribuidora` parametrizado, `calcula_coordenadas`.
* `process_data.py`: `fill_email_model`, `prepare_*`, `get_address` (usa `MAPS_KEY`).

# Problemas

* `fill_movimiento` y `fill_ruta` usan `DIC_SABANAS_MOV` sin importarlo. Si se invocan, dan `NameError`.
* `calcula_modelo`, `union_cap_tables` y `get_address` están comentados en `catalog.py`.
* `unir_tablas` descarta silenciosamente adjuntos cuando la estructura cambia.
* Imprime el texto completo del correo en logs. Ver [seguridad](../riesgos/seguridad.md).

# Duplicación

`unir_tablas`, `normalizar_texto`, `eliminar_stopwords`, `detectar_tipo_correo` y `process_data` están copiados en varios módulos. Ver [deuda técnica](../riesgos/deuda-tecnica.md).

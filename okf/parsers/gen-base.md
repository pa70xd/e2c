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

* `fill_movimiento` y `fill_ruta` de `gen_parse/process_data.py` (sin importar `DIC_SABANAS_MOV`, `NameError`) se borraron en la rama `claude/e2c-limpieza` (mergeada).
* `calcula_modelo`, `union_cap_tables` y `get_address` están comentados en `catalog.py`.
* `unir_tablas` descarta silenciosamente adjuntos cuando la estructura cambia.
* Imprime el texto completo del correo en logs. Ver [seguridad](../riesgos/seguridad.md).

# Duplicación

En la rama `claude/e2c-core-parsers` (Fase 2, mergeada) existe `parsers/core/` con **una** implementación de `unir_tablas` (`tablas.py`), `normalizar_texto`, `eliminar_stopwords`, `convertir_html_a_texto` (`texto.py`) y `detectar_tipo_correo` (`correo.py`). `DANONE_UTILS`/`GEN_UTILS`/`PENAFIEL_UTILS` (`utils.py`) y `DANONE_READER`/`GEN_READER`/`PENAFIEL_READER` (`reader.py`) las re-exportan con los mismos nombres, y Holanda y Heineken las heredan vía `DANONE_*`. Según la sesión, las copias no diferían en comportamiento (comparadas por AST; solo cambia el nombre de clase en `convertir_html_a_texto`); esa comparación no la repetí, pero los goldens no cambiaron. Siguen duplicadas: `process_data`, `safe_filename`, `sql_list` y `normalize` (readers). El bug de stopwords antes del regex en `analizar_proposito` de Danone queda intacto (xfail).

Lo que antes figuraba aquí como "copiado en varios módulos" ya no aplica, salvo lo listado como duplicado. Ver [deuda técnica](../riesgos/deuda-tecnica.md). Ver [deuda técnica](../riesgos/deuda-tecnica.md).

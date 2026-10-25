---
type: Known Issues
title: Código muerto del orquestador
description: Módulos y funciones que existen en el repo pero no se llaman desde el flujo.
tags: [codigo-muerto, deuda-tecnica]
---

# Sin importadores

* `src/attachments.py` (`DanoneAttachments`): nadie lo importa. Tiene `finally: pass` sin efecto y `output_dir="debuger"` (línea 22; es nombre de carpeta en disco, renombrarlo cambia comportamiento). La limpieza de la Fase 2 no lo tocó.
* `models/service_request.py` (`Template_Sabana`): solo aparece en un comentario de `service.py`.
* `config/config_general/movimientos_list.py`: sin importadores.
* `infrastructure/graphapi/graphapi.py`: `getTemplate` y `send_mail_file` (0 usos verificados con `grep`). El bloque comentado de `reply_mail` y `reply_mail_v4` se borró en la Fase 2 (`claude/e2c-limpieza`, mergeada).
* `infrastructure/tableau/tableau.py`: `getModelo`.
* `infrastructure/database/engine_duck.py`: sin hallazgos, pero se usa poco.
* `parsers/kof.py`: stub, no registrado. Ver [KOF](../parsers/kof.md).

# Borrado en la Fase 2 (rama `claude/e2c-limpieza`, mergeada)

Verificado con `git grep` en la rama: `detect_purpose`, `union_cap_tables` y `complet_catalog_line` de `danone_parse/process_data.py`; `fill_movimiento` y `fill_ruta` de `gen_parse/process_data.py`; `complet_catalog_line` de `penafiel_parse/catalog.py`; cinco métodos de `messages.py` sin llamadas; la primera `msj_fail`. Detalle en [deuda técnica](../riesgos/deuda-tecnica.md).

# Pendiente de confirmar

* `danone_parse/process_data.py`: `get_categoria_linea`, `fill_movimiento`, `fill_ruta` (los métodos del mismo nombre en `DANONE_SABANA` son de otra clase).
* `penafiel_parse/process_data.py` y `gen_parse/process_data.py`: `detect_purpose`.
* `src/email_type.py::_is_auto_submitted` (stub + sobrescritura).

# Lista de decisiones

Antes de borrar cualquiera de estos, confirmar con el equipo. Algunos pueden ser piezas que se retomarán.

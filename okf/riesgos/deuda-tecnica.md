---
type: Risk Register
title: Deuda técnica
description: Duplicación, código muerto y configuración que debería ser datos.
tags: [deuda-tecnica, mantenibilidad]
---

# Duplicación

* Clase `DB_POSTGRE` idéntica en Danone, Penafiel y Gen. ~650 líneas cada una. **En la rama `claude/e2c-core-repository` (Fase 2, mergeada) queda una base común `DBPostgreBase` en `repository/core/` y cada cliente solo conserva sus overrides.** Ver [capa de repositorio](../data/capa-repositorio.md).
* `unir_tablas`, `normalizar_texto`, `eliminar_stopwords`, `convertir_html_a_texto` y `detectar_tipo_correo` copiados en 3 utilidades. **En la rama `claude/e2c-core-parsers` (Fase 2, mergeada) quedan unificados en `parsers/core/`**; sigue duplicado `process_data` (más `safe_filename`, `sql_list`, `normalize` de los readers).
* Comandos bot implementados 4 veces: Danone, Penafiel, Holanda, Heineken. **En la rama `claude/e2c-bot-commands` (Fase 2, mergeada) quedan unificados en `bot/commands.py` con un `PerfilBot` por cliente.** Ver [respuesta y comandos](../flows/respuesta-y-comandos.md).
* INSERT de `cooler_request` en 5 variantes de SQL.
* `get_cbu_name` y `get_cbu_names_valid` idénticos entre Danone y Penafiel.
* `IGNORE_REQUESTS` idéntico entre Danone y Penafiel.
* `NAMES_COLUMNS` de Penafiel copia el bloque de Danone.
* Cuatro estrategias distintas para pintar originales rechazados.
* `SC | Sin Canal` en cuatro lugares. `DUPLICADO` en dos.
* Tres versiones de `solicitudes_rechazadas`.

# Código muerto

Ver [código muerto del orquestador](../services/codigo-muerto.md) y las listas en cada parser. Lista resumida:

* `danone_parse/process_data.py`: `detect_purpose`, `union_cap_tables` y `complet_catalog_line` **borrados en la rama `claude/e2c-limpieza`** (0 usos). Se conservan `fill_movimiento`, `fill_ruta` (los métodos con ese nombre en `DANONE_SABANA` son de otra clase; la sesión los considera casi seguros muertos) y `get_categoria_linea` (usada desde `DANONE_CATALOG`, sin llamador ya en su clase). Pendiente de confirmar.
* `gen_parse/process_data.py`: `fill_movimiento` y `fill_ruta` (import comentado, `NameError`) **borrados en la rama `claude/e2c-limpieza`**. `detect_purpose` sigue en `gen_parse` y `penafiel_parse/process_data.py` (fuera de la lista, no tocado).
* `penafiel_parse/catalog.py`: `complet_catalog_line` (llamaba a un método que no existe) **borrado en la rama `claude/e2c-limpieza`**.
* `messages.py`: `msj_apertura`, `msj_respuesta`, `msj_reply_update_coolers`, `msj_reply_add_customer_cooler`, `msj_solicitud_completa` **borrados en la rama `claude/e2c-limpieza`** (se conserva `msj_solicitud_completa_esc1`).
* Código comentado en `graphapi.py` (`reply_mail` y `reply_mail_v4`): **borrado en la rama `claude/e2c-limpieza`**.
* `src/attachments.py` sin importadores (carpeta de salida literal "debuger"; no tocado). `src/email_type.py::_is_auto_submitted` (stub + sobrescritura, líneas ~217/220): no tocado.
* Rama `claude/e2c-limpieza` mergeada en la base (`9564d90`): 3 commits (`fa37826`, `085c4b3`, `259aa74`); `tests/golden` sin diff. Lo que se borró: 715 líneas.

# Configuración que debería ser datos

* Catálogos de modelos y distribuidoras en Python. Cambian con frecuencia.
* Tablas de servicio D2D de Heineken como tuplas posicionales.
* Mapa CBU a cliente.
* Lista de remitentes de Holanda.
* Mensajes con "Estimado usuario REPARE" literal.
* Regex de clasificación por cliente, cientos de líneas.

# Nombres y typos

* `TIPOS_SERVICIO_VALIDOSs` (renombrado a `TIPOS_SERVICIO_VALIDOS` en la rama `claude/e2c-limpieza`; única ocurrencia), `FECHA SOLCITUD` (`columns_names.py:17`), `DIREECIÓN` (`columns_names.py:56`) y `Ocurrio` (`fails_response.py:27`): estos tres son strings visibles a clientes o Excel y siguen sin corregir.
* `debuger` en lugar de `debug`.
* Variable `flujo` sin uso.
* Función `_is_auto_submitted` con stub y sobrescritura.

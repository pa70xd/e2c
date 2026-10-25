---
type: Risk Register
title: Deuda técnica
description: Duplicación, código muerto y configuración que debería ser datos.
tags: [deuda-tecnica, mantenibilidad]
---

# Duplicación

* Clase `DB_POSTGRE` idéntica en Danone, Penafiel y Gen. ~650 líneas cada una.
* `unir_tablas`, `normalizar_texto`, `eliminar_stopwords`, `convertir_html_a_texto` y `detectar_tipo_correo` copiados en 3 utilidades. **En la rama `claude/e2c-core-parsers` (Fase 2, sin mergear) quedan unificados en `parsers/core/`**; sigue duplicado `process_data` (más `safe_filename`, `sql_list`, `normalize` de los readers).
* Comandos bot implementados 4 veces: Danone, Penafiel, Holanda, Heineken.
* INSERT de `cooler_request` en 5 variantes de SQL.
* `get_cbu_name` y `get_cbu_names_valid` idénticos entre Danone y Penafiel.
* `IGNORE_REQUESTS` idéntico entre Danone y Penafiel.
* `NAMES_COLUMNS` de Penafiel copia el bloque de Danone.
* Cuatro estrategias distintas para pintar originales rechazados.
* `SC | Sin Canal` en cuatro lugares. `DUPLICADO` en dos.
* Tres versiones de `solicitudes_rechazadas`.

# Código muerto

Ver [código muerto del orquestador](../services/codigo-muerto.md) y las listas en cada parser. Lista resumida:

* `danone_parse/process_data.py`: `detect_purpose`, `fill_movimiento`, `fill_ruta`, `union_cap_tables`, `complet_catalog_line`, `get_categoria_linea`.
* `gen_parse/process_data.py`: `fill_movimiento` y `fill_ruta` con import comentado (`NameError`).
* `penafiel_parse/catalog.py`: `complet_catalog_line` llama a un método que no existe.
* `messages.py`: `msj_apertura`, `msj_respuesta`, `msj_reply_update_coolers`, `msj_reply_add_customer_cooler`, `msj_solicitud_completa`.
* Código comentado en `graphapi.py` (líneas 198-223 y 360-520).

# Configuración que debería ser datos

* Catálogos de modelos y distribuidoras en Python. Cambian con frecuencia.
* Tablas de servicio D2D de Heineken como tuplas posicionales.
* Mapa CBU a cliente.
* Lista de remitentes de Holanda.
* Mensajes con "Estimado usuario REPARE" literal.
* Regex de clasificación por cliente, cientos de líneas.

# Nombres y typos

* `TIPOS_SERVICIO_VALIDOSs`, `FECHA SOLCITUD`, `DIREECIÓN`, `Ocurrio`.
* `debuger` en lugar de `debug`.
* Variable `flujo` sin uso.
* Función `_is_auto_submitted` con stub y sobrescritura.

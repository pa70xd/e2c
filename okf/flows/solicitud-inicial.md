---
type: Process Flow
title: Solicitud inicial
description: Flujo de un correo nuevo con Excel adjunto, desde la validación del propósito hasta la respuesta con tres Excel.
resource: https://github.com/pa70xd/e2c/blob/claude/admiring-lovelace-3oh7g0/parsers/danone.py
tags: [flujo, parseo, excel, validacion]
---

# Pasos comunes (Danone, Penafiel, Heineken, Holanda)

1. **Propósito**: el cuerpo HTML se convierte a texto y se evalúa con regex. Hay listas de ignorar y de aceptar (`CREATE_REQUESTS`, `MOVEMENTS`). Ver [parsers](../parsers/gen-base.md).
2. **Gate de duplicado**: `email_init_exist` por `graph_message_id`. Si ya existe, se omite.
3. **Adjuntos**: solo `.xlsx` y `.xls` en Danone; Penafiel acepta `.xlsm`. Se lee la primera hoja visible.
4. **Normalización**: alias de columnas (`NAMES_COLUMNS`) a nombres canónicos. Columnas faltantes se crean vacías.
5. **Unión**: `unir_tablas` hace UNION ALL de los Excel. Si cambia la estructura, se descarta el resto sin aviso.
6. **Catálogos**: distribuidora por código postal (CP) y tipo de movimiento; coordenadas con geocodificación; modelo y línea (ver nota abajo).
7. **Reglas de negocio**: cada cliente tiene su `business.py`. Las filas que fallan van a `solicitudes_rechazadas`.
8. **Sábanas**: se generan `pre_sabana`, `sabana_movimiento`, `sabana_ruta` y `solicitud` con DuckDB.
9. **Persistencia**: `save_email_log_init`, `send_email_request`, `send_email_coolers` por fila, `update_email_request`.
10. **Respuesta**: correo con `msj_send_presabana` y adjuntos. Si falla el parseo, responde `formato_desconocido` o no responde.

# Nota sobre modelo y línea

En Danone y Penafiel, `calcula_modelo` era un stub (corregido en parte en la rama `claude/e2c-modelos`, sin mergear: ver [bugs](../riesgos/bugs.md)): solo agrega columnas `*_GEN` vacías. Modelo, categoría y línea quedan NULL. Ver [bugs](../riesgos/bugs.md#modelo-categoria-y-linea-no-se-llenan).

# Orden de escritura (riesgo)

El flujo escribe en PostgreSQL antes de responder. Si una etapa falla a mitad, la solicitud queda a medias y el correo ya quedó marcado como procesado. No hay transacción. Ver [capa de repositorio](../data/capa-repositorio.md).

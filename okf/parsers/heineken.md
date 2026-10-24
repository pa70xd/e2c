---
type: Client Integration
title: Parser Heineken
description: "Parser del buzón cliente.hnk@. Dos flujos por asunto: D2D (precarga) y RUTA (mantenimiento)."
resource: https://github.com/pa70xd/e2c/blob/claude/admiring-lovelace-3oh7g0/parsers/heineken.py
tags: [heineken, cervecero]
---

# Flujos por asunto

* **D2D**: asunto con `PRECARGA` y `D2D`.
* **RUTA**: asunto con `MANTENIMIENTO FERGUEZ`.

# Lectura

* Busca la cabecera en las primeras 10 filas con marcadores `MODELO` y `SERIE`.
* Valores `0`, `NA`, `N/A`, `-` se convierten a nulo.
* CP con `zfill(5)` si tiene 5 dígitos o menos.
* Teléfono solo dígitos.

# D2D

* Canal → puesto → distribuidora (ver config). Falla → categoría, línea, tipo de servicio y prefijo de serie genérica.
* Serie `ASIGNAR SERIE GENERICA` se resuelve en Postgres con prefijo `HEI` o `MOB`.
* Reglas: cliente detallista, serie, ID de servicio y distribuidora no pueden ser nulos.
* Duplicados: series con caso abierto en Postgres → OS `DUPLICADO`. No hay dedupe dentro del lote.
* Cambios (`RETIRO POR CAMBIO`, `CAMBIO DE ENF`) generan solo retiro, sin entrega del equipo de reemplazo. Confirmar con negocio.

# RUTA

* CP nulo o serie nula rechazan la fila.
* Tipo de movimiento fijo `REPARACION MERCADO`.
* Distribuidora ruta fija `500166 | D1604 | DIST. CM VALLEJO REHAB. - COACALCO`. El catálogo tiene el nombre sin `D1604`.

# Estado OS

Vacía → REJECTED; dígitos con 403 → ACCEPTED; resto → PENDING.

# Problemas

* No verifica que queden filas válidas tras las reglas. Puede crear solicitud con total 0.
* Devuelve mensaje como dict.
* Usa `DANONE_READER.detectar_tipo_correo` para comandos.
* `bot.cancelar` cancela pendientes y solicitud. Es el único cliente que lo hace bien junto con Holanda.

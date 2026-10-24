---
type: Integration
title: Geocodificación Google
description: Geocodificación inversa de código postal, colonia, ciudad y estado para filas de Holanda y coordenadas de Danone y Penafiel.
resource: https://github.com/pa70xd/e2c/blob/claude/admiring-lovelace-3oh7g0/infrastructure/geocoding/geocoding.py
tags: [google-maps, geocodificacion]
---

# Uso

* `GEOCODING.calcula_coordenadas` llena CP_GEN, COLONIA_GEN, CIUDAD_GEN, ESTADO_GEN y PAIS_GEN por fila. Lo usa Holanda.
* En Danone y Penafiel, `get_address` en `process_data` hace reverse geocoding por fila.
* Variable: `MAPS_KEY`.

# Problemas

* Una llamada por fila, sin caché ni límite de tasa.
* `requests.get` sin timeout.
* Consulta SQL armada con f-string en líneas 90 y 101.
* Hay dos claves: `MAPS_KEY` en uso y `GOOGLE_MAPS_API_KEY` en código muerto.
* El docstring dice que Danone y Penafiel tienen copias idénticas. Ya no es cierto.

Ver [deuda técnica](../riesgos/deuda-tecnica.md).

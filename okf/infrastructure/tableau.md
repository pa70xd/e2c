---
type: Integration
title: Tableau
description: Consultas VizQL a Tableau para puntos de venta y modelos activos o con serie.
resource: https://github.com/pa70xd/e2c/blob/claude/admiring-lovelace-3oh7g0/infrastructure/tableau/tableau.py
tags: [tableau, vizql]
---

# Uso activo

* `getPtoVentaData`: datos de puntos de venta.
* `get_modelo_act_ser`: modelos activos y series.

# Sin uso

* `getModelo`.

# Variables

* `PROJECT_ID` (con valor por defecto), `TOKEN_NAME`, `TOKEN_SECRET`.
* Constantes: `URL_BASE`, API 3.25, datasource LUID repetido en tres lugares.

# Problemas

* Login en cada consulta, sin caché.
* Requests sin timeout.
* `raise` sin excepción activa en tres lugares. Produce `RuntimeError` confuso.
* `get_modelo_act_ser` devuelve `[]` en silencio si falla.
* Rama `else` muerta.

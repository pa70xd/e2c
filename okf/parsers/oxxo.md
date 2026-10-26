---
type: Module
title: Oxxo (mantenimiento y garantías)
description: Parsers deterministas (sin LLM) para los buzones de Oxxo, apagados por defecto. Fase 4, rama claude/e2c-oxxo, sin mergear.
tags: [parsers, oxxo, fase-4]
---

# Estado

Rama `claude/e2c-oxxo` (commit `0278796`), **sin mergear**. Verificado en la rama: existen `parsers/oxxo.py`, `parsers/oxxo_parse/{plantillas,excel,process_data,habilitado}.py`, `repository/oxxo/` (con 7 SQL) y 4 clases registradas en `src/service.py` (`OXXO_INIT`, `OXXO_REPLY`, `OXXO_GARANTIAS_INIT`, `OXXO_GARANTIAS_REPLY`); `python -m pytest -q` → **1009 passed, 56 skipped, 1 xfailed**. Los 56 skip incluyen tests contra PostgreSQL; la sesión dice haber verificado además el SQL de Oxxo contra un PG16 local desechable (10 de 10): no lo repetí.

# Apagado por defecto

Solo corre si `oxxo` / `oxxo_garantias` están en `E2C_CLIENTES_HABILITADOS` (lista separada por comas, se lee en cada llamada; verificado en `parsers/oxxo_parse/habilitado.py`). Motivo: Oxxo ya tiene una **PoC automatizada fuera del repo**; con ambas sobre el mismo buzón **se duplican las OS**, y el dedupe del repo no protege contra la PoC (según la sesión). Ver [decisiones](../riesgos/decisiones.md).

# Dos buzones

* `oxxo` (mantenimiento) y `oxxo_garantias` (garantías, buzón de rol `cliente.oxogar`).
* **Sin LLM:** regex por campo etiquetado; tolera acentos, mayúsculas, espacios y líneas extra.

# Reglas (según la sesión)

* **Mantenimiento** (asunto "Abierto-Asignado ----> <ticket>"): OS nueva de ruta, folio = ticket de 8 dígitos exactos, sin serie. Ticket faltante o inconsistente → aviso "requiere revisión" a REPARE; no se guarda ni se inventa.
* **Garantías** "Seguimiento a Folio: <folio>": es **escalación**. Folio ya en base → se marca en `gestion_observaciones` (el status no cambia) y se avisa por el canal de `review/` (motivo `escalacion_garantia`). Folio inexistente → OS nueva de garantía con aviso en la respuesta.
* **Garantías con Excel** (`.xlsx`/`.xlsm`, "Lay Out Repare"): si el cuerpo dice "N OS", el Excel debe traer N filas o va a revisión sin persistir.
* **Dedupe** por ticket/folio entre ambos buzones (`INSERT ... WHERE NOT EXISTS` sobre `folio` en `cooler_request`, cliente OXXO/OXXO_GARANTIAS) más `email_init_exist` por mensaje.
* Mapeo a `cooler_request` documentado en el encabezado de `repository/oxxo/consultas_postgre.py`. Datos personales solo en campos ya previstos; el correo del solicitante no se guarda; no se loguea nada.

# Límites y pendientes

* El **lector común** (`parsers/core/lector.py`) aún no está en la base: `excel.py` es provisional con `openpyxl`.
* `config/email_index.json` de esta rama **no** tiene los buzones de Oxxo (verificado: 0 coincidencias); vienen en `claude/e2c-lector-excel`.
* Plaza y nombre de tienda llegan juntos sin delimitador: van en `razon_social` y plaza queda NULL.
* Las OS entran **sin** código postal, coordenadas, distribuidora ni pre-sábana.
* El outbound REPARE → Oxxo no se concilia. Prioridad MEDIA fija (la de la plantilla va en `gestion_observaciones`).

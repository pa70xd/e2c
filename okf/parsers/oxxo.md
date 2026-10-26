---
type: Module
title: Oxxo (mantenimiento y garantías)
description: Parsers deterministas (sin LLM) para los buzones de Oxxo, apagados por defecto. Fase 4, rama claude/e2c-oxxo, sin mergear.
tags: [parsers, oxxo, fase-4]
---

# Estado

Rama `claude/e2c-oxxo` (commits `0278796` y `ecd3c57`), aprobada por la orquestadora y en merge (**no confirmado en la base** al escribir esto). Verificado en la rama: existen `parsers/oxxo.py`, `parsers/oxxo_parse/{plantillas,excel,process_data,habilitado}.py`, `repository/oxxo/` (con 7 SQL) y 4 clases registradas en `src/service.py` (`OXXO_INIT`, `OXXO_REPLY`, `OXXO_GARANTIAS_INIT`, `OXXO_GARANTIAS_REPLY`); `python -m pytest -q` en la rama → **1153 passed, 2 failed, 56 skipped, 1 xfailed** en mi contenedor; los 2 fallos son por no tener `odfpy` (1153 + 2 = 1155, la cifra de la sesión). Los 56 skip incluyen tests contra PostgreSQL; la sesión dice haber verificado además el SQL de Oxxo contra un PG16 local desechable (10 de 10): no lo repetí.

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

# Actualización final (`ecd3c57`)

* El Excel de garantías ya se lee con el [lector común](lector.md) (`parsers/oxxo_parse/excel.py`, verificado), con hojas ocultas `nunca` para no duplicar OS.
* El interruptor delega en `src.email_type.cliente_habilitado` (verificado en `habilitado.py`): una sola fuente de verdad, `E2C_CLIENTES_HABILITADOS`.

# Puntos abiertos (de la sesión)

1. **Duplicado con la PoC:** si se enciende `oxxo`/`oxxo_garantias` mientras la PoC externa siga leyendo el mismo buzón, cada ticket/folio genera dos OS. El dedupe del repo solo protege de reprocesos propios. **El corte lo decide REPARE.**
2. Las OS entran sin CP, coordenadas, distribuidora ni pre-sábana; sábanas y Tableau no las verán completas.
3. Plaza vacía: la plantilla junta "<plaza> <nombre tienda>" sin delimitador; todo va en `razon_social` y `plaza` queda NULL (no se inventó el corte). Falta confirmar el formato con Oxxo.
4. El outbound REPARE → Oxxo no se concilia (devuelve `None`).
5. **Carrera residual:** entre `get_by_folio` y el INSERT otra instancia puede ganar el folio; el INSERT no duplica la fila, pero queda un `email_request` huérfano (total 1, sin fila).
6. Los buzones de Oxxo vienen en `email_index.json` de la rama del lector (ya en la base); la prioridad se guarda MEDIA (la de la plantilla va en `gestion_observaciones`) y el correo del solicitante no se guarda.

# Límites anteriores

* El **lector común** (`parsers/core/lector.py`) aún no está en la base: `excel.py` es provisional con `openpyxl`.
* `config/email_index.json` de esta rama **no** tiene los buzones de Oxxo (verificado: 0 coincidencias); vienen en `claude/e2c-lector-excel`.
* Plaza y nombre de tienda llegan juntos sin delimitador: van en `razon_social` y plaza queda NULL.
* Las OS entran **sin** código postal, coordenadas, distribuidora ni pre-sábana.
* El outbound REPARE → Oxxo no se concilia. Prioridad MEDIA fija (la de la plantilla va en `gestion_observaciones`).

---
type: Client Integration
title: Parser Danone / Bonafont
description: Parser del buzón cliente.danone@. Cliente piloto de Email to Case. Movimientos y rutas.
resource: https://github.com/pa70xd/e2c/blob/claude/admiring-lovelace-3oh7g0/parsers/danone.py
tags: [danone, bonafont, piloto]
---

# Entradas

* `parsers/danone.py`: `DANONE_INIT` y `DANONE_REPLY`.
* `parsers/danone_parse/`: `reader`, `utils`, `business`, `catalog`, `sabana`, `process_data`.
* Config en `config/customers/danone/`. Ver [reglas por cliente](../clients/reglas-por-cliente.md).

# Flujo particular

* Propósito: `IGNORE_REQUESTS` y luego `CREATE_REQUESTS` o `MOVEMENTS`.
* Solo `.xlsx` y `.xls`. Cabecera BNF/IVY con `skiprows=2` fijo.
* Serie: rechaza si `SERIE DNN/BNF` y `SERIE FABRICANTE` están vacías.
* CBU válido: ONE DANONE, DANONE, EDP, ONE COOLER → DANONE; BONAFONT, BNF → BONAFONT.
* Prioridad HIGH.
* Estado OS: vacía → REJECTED; contiene `[RECHAZADO]` → PENDING; sin prefijo 403 → PENDING; resto → ACCEPTED.
* Coordenadas: reverse geocoding por fila.
* Total de coolers: `COUNT(*)` de `solicitud`, que incluye rechazadas. No cuadra con los coolers guardados.

# Problemas verificados

* `calcula_modelo` es stub. Modelo, categoría y línea quedan NULL. Ver [bugs](../riesgos/bugs.md).
* `convertir_html_a_texto` quita stopwords antes de evaluar regex de propósito. Si los patrones contienen stopwords, no matchean. Impacto por probar con correos reales.
* `bot.cancelar` no cancela coolers. Un outbound posterior reabre la solicitud. Corregido en rama `claude/e2c-fix-parsers`, sin mergear.
* `TRASLADO` aparece en `movimientos_danone.py` pero no en `DIC_SABANAS_MOV`. Probable rechazo de traslados.
* Regex `\avisos` y `\aviso` (líneas 164-165) con `\a` que es BEL. Nunca coinciden. Verificado. Corregido mergeado en `claude/admiring-lovelace-3oh7g0` (rama `claude/e2c-fix-mecanicos`), también en Penafiel.
* `failed_coolers` siempre 0.

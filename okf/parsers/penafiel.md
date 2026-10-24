---
type: Client Integration
title: Parser Penafiel (KDRP)
description: Parser del buzón cliente.kdrp@. Mismo flujo que Danone con diferencias de lectura, serie y distribuidora.
resource: https://github.com/pa70xd/e2c/blob/claude/admiring-lovelace-3oh7g0/parsers/penafiel.py
tags: [penafiel, kdrp]
---

# Entradas

* `parsers/penafiel.py` y `parsers/penafiel_parse/`.
* Config en `config/customers/penafiel/`. Ver [reglas por cliente](../clients/reglas-por-cliente.md).

# Diferencias con Danone

* Propósito: concatena cuerpo y asunto sin separador (`penafiel.py:60`). Usa `gen_parse` para normalizar, sin quitar stopwords.
* Lector: usa `gen_reader.get_adjuntos`, acepta `.xlsm`, no maneja BNF/IVY.
* CBU fijo a `PENAFIEL` (`penafiel_parse/reader.py:49-50`).
* Descarta en silencio filas con `SERIE`, `SERIE FABRICANTE` y `MODELO` vacíos.
* Serie: exige solo `SERIE`, aunque el comentario dice otra cosa.
* Distribuidora: `gen_parse/catalog.py` sin fallback a CP si falla `CP_GEN`.
* `penafiel.py:230` compara `DEBUG == "True"` con un bool. Nunca se cumple.

# Problemas verificados

* Regex sin `\b` inicial en `movimientos_penafiel.py:127`.
* Patrones con mayúsculas o acentos inalcanzables porque el texto se normaliza antes (`OS`, `traslád...`).
* CBU `PEÑAFIEL`: pasa la validación pero no obtiene distribuidora, porque la búsqueda usa mayúsculas y la clave está en minúsculas.
* DIRECCION es obligatoria en `EXPECTED_COLUMNS` pero sus alias están comentados. La columna del archivo se descarta.
* Imprime `DB_HOST` y `DB_NAME` en logs de depuración.

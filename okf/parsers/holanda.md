---
type: Client Integration
title: Parser Holanda (Helados)
description: Parser del buzón cliente.holanda@. Casos por folio CASO2, origen Heladio o GDR, sin hilo.
resource: https://github.com/pa70xd/e2c/blob/claude/admiring-lovelace-3oh7g0/parsers/holanda.py
tags: [holanda, helados, unilever]
---

# Entradas

* `parsers/holanda.py`, `parsers/holanda_parse/`.
* Config en `config/customers/holanda/`.

# Flujo particular

* Gate de asunto: tras quitar `[..]`, `RE:` y `FW:`, debe ser `casos repare`. Si no, se ignora sin respuesta.
* No usa hilo. Cada correo con Excel crea una solicitud. Comandos del bot por folio `REPARE_\d+`.
* Origen desde el sufijo de CASO2: `H` → HELADIO, `G` → GDR. Otro origen rechaza la fila.
* Fecha en DD/MM/AAAA o ISO. Teléfono solo dígitos; para HELADIO, `521` + 10 dígitos → 10.
* Serie `X/CONG` → `X` si coincide con CONGELADOR.
* Fallback posicional: columna 33 = OS, columna 34 = MERMA.
* Duplicados: clave `COALESCE(CONGELADOR, SERIE)`. Dentro del lote gana TE menor, luego FECHA más antigua. Contra Postgres marca OS = `DUPLICADO`. Las duplicadas siguen en la tabla.
* Distribuidora por CP con `get_distribuidora_ruta`.
* Espejo de merma: por cada fila válida se genera una fila con serie + `M`.
* Prioridad MEDIUM en process_data y MEDIA en SQL. Inconsistente.

# Problemas

* Outbound cuenta todas las OS como "con OS" sin aplicar la regla 403.
* `pd.read_excel` toma la primera hoja aunque esté oculta.
* `business.py` devuelve `rechazadas == 0`, con semántica invertida frente al resto. El caller lo ignora.
* Si `presabana` es None, retorna después de guardar solicitud y coolers.
* Mensaje de respuesta como dict en vez de str (`fails_response.py`).
* Pendientes de negocio: "CONFIRMAR MODELO" sin catálogo, responsable sin correo real. Ver [preguntas abiertas](../riesgos/preguntas-abiertas.md).

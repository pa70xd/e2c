---
type: Findings
title: Análisis de 21 correos reales
description: Resumen redactado de lo que mostró un análisis local de 21 correos reales (2026-10-26). No contiene el contenido de los correos ni datos personales.
tags: [pruebas, correos-reales, clasificador, bugs]
---

# Alcance y reserva

El usuario compartió 21 correos reales (.eml). La orquestadora los analizó **localmente, sin salir del contenedor**; este resumen es suyo y **no incluye contenido de los correos, remitentes ni direcciones**. Las cifras sobre los 21 correos no las pude verificar (no tengo los .eml). Sí verifiqué en el código los puntos marcados "verificado".

# Línea base de regex sobre los 21

* Precisión de gate 0.81; 15 de 21 tipos de evento correctos; 0 de 5 filas del cuerpo.
* Es una muestra pequeña: no sustituye un set real etiquetado.

# Hallazgos

## 14 de 21 nunca entran al sistema

`config/email_index.json` solo mapea los buzones de cuatro clientes: danone, holanda, kdrp y hnk (verificado: el archivo tiene cinco claves, cuatro de cliente y una de un buzón personal, ver más abajo). **Imbera, oxxo, oxogar, torrey y kof no están.** Es una **decisión de alcance pendiente con el usuario**: ¿se incorporan esos clientes?

## Holanda descarta todo (bug)

`es_asunto_holanda` (`parsers/holanda.py:70`) compara el asunto normalizado con `ASUNTO_HOLANDA` de forma exacta ("casos repare"; ignora mayúsculas, prefijos `RE:`/`RV:`/`FW:` y etiquetas `[..]`). Verificado en el código. Según el análisis, el asunto real lleva una fecha, así que **Holanda descarta todo, incluida la conciliación de OS**. **Corregido en la rama `claude/e2c-fix-holanda-indice` (`330763f`, sin mergear)**: el asunto acepta fecha o sufijo numérico; esa rama también saca un correo personal del índice (variable opcional `E2C_TEST_MAILBOX`). Verificado ejecutando la función y `pytest -q` → 829 passed, 48 skipped, 1 xfailed.

## Dirección y etapa

* La **etapa** sale solo del prefijo "RE:" (verificado en `src/email_type.py`, que revisa prefijos del asunto); no usa `In-Reply-To`. Hay solicitudes nuevas que llegan con RE: y respuestas sin RE:.
* `detect_direccion` mira solo el `To:` (verificado: usa `email.to_recipients`). Según el análisis, confunde correos internos de REPARE con outbound, y un pedido de una persona de REPARE con inbound del cliente.

## Lectura de Excel

* `.ods` no se acepta; Holanda no acepta `.xlsm`.
* Los encabezados de Imbera ocupan de 2 a 4 filas; hay filas basura de una celda.
* Las hojas ocultas de KOF no se leen (12 equipos).

## Outbound

El outbound solo concilia por Excel: las OS que REPARE comparte en texto se pierden.

## Patrones que faltan en el prompt del clasificador

Correos de salida de REPARE; notificaciones de sistemas del cliente (tickets de Oxxo, call center de Holanda); escalación de un folio no atendido (en init no existe "estatus"); pedidos internos de REPARE; garantía (factura, placa, buzón de garantías); vocabulario real (CAMBIO DE EQUIPO, COBERTURA, EQUIPO ADICIONAL, NO ENFRIA, CONDENSACION); tablas aplanadas en el cuerpo; IDs `IMB-`/`REP-`; cuerpos de una línea con el dato en el Excel; datos que solo están en el correo citado.

## `redact()` dejó pasar datos personales (BLOQUEANTE)

Sobre los 21 correos, `redact()` no cubrió: 53 nombres, 7 direcciones, 6 coordenadas, 1 URL de mapa, 2 correos y 3 montos (patrones F1-F9). **No activar `CLASSIFIER_SHADOW` ni haiku con correos reales hasta mergear `redact-v2`** (`session_01GRj3nHJi8AeCXJdsKvwAEY`, rama `claude/e2c-redact-v2`). Consecuencia: el [modo sombra](../riesgos/decisiones.md) y cualquier corrida con key sobre correos reales mandarían datos personales a un proveedor externo. Ya había un límite conocido en [redact](../classifier/redact.md) (nombres sin despedida ni etiqueta no se detectan).

# Relación con otros documentos

[Bugs](../riesgos/bugs.md), [runbook del lunes](../deploy/runbook-lunes.md), [evaluación](evaluacion.md) (el set real saldrá de aquí, ya redactado y revisado a mano).

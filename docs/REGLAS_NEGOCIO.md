# Reglas de negocio (extraídas del código)

Inventario de lo que el sistema decide hoy, sacado del código. No es la verdad del negocio: es lo que el código hace. Cada regla debe confirmarse con el owner. Marcar en la columna **Estado** como `OK`, `Obsoleta` o `Incorrecta`.

## 1. Entrada de correos (`src/email_type.py`, `src/service.py`)

| # | Regla | Estado |
|---|-------|--------|
| E1 | Se ignora: borrador, asunto vacío, cuerpo vacío, sin fecha, invitaciones de calendario | |
| E2 | Se ignora si el header `Auto-Submitted` ≠ `no` o existe `X-Auto-Response-Suppress` | |
| E3 | Se ignora remitente `errorreportingnotifications-noreply@google.com` | |
| E4 | Se ignora por asunto: respuesta automática, fuera de oficina, rebotes, acuses de lectura | |
| E5 | Es "respuesta" si el asunto empieza con `re:`, `rv:`, `fw:`, `fwd:` o hay header `In-Reply-To`/`References` | |
| E6 | Cliente = buzón (a/cc) que aparezca en `config/email_index.json`; si no, el remitente | |
| E7 | Dirección: `bot` (REPARE→REPARE con "estimado usuario repare"), `reply_to_bot`, `inbound`, `outbound` | |
| E8 | Correo duplicado = mismo `internet_message_id` en menos de 120 s. **Vive en memoria**: se pierde al reiniciar y no se comparte entre instancias | |

## 2. Filtros por cliente

| # | Cliente | Regla | Estado |
|---|---------|-------|--------|
| F1 | Heineken | Asunto debe contener `PRECARGA`+`D2D` (flujo D2D) o `MANTENIMIENTO FERGUEZ` (flujo Ruta) | |
| F2 | Holanda | Solo asunto `casos repare` (sin mayúsculas, sin `RE:/RV:/FW:`, sin etiquetas `[..]`) | |
| F3 | Danone | El cuerpo debe coincidir con alguno de los patrones de `CREATE_REQUESTS` (`config/customers/danone/movimientos_danone.py`) | |
| F4 | KOF | Sin implementar (`parsers/kof.py` es un stub de 5 líneas) | |

## 3. Rechazo de filas (pre-creación)

Todo lo que incumple se mueve a `solicitudes_rechazadas` con su motivo.

### Danone (`parsers/danone_parse/business.py`) y Peñafiel (`parsers/penafiel_parse/business.py`)

| # | Regla | Motivo | Estado |
|---|-------|--------|--------|
| D1 | Faltan columnas mínimas (`EXPECTED_COLUMNS`) → se rechaza el archivo completo | columnas faltantes | |
| D2 | Danone: sin `SERIE DNN/BNF` **y** sin `SERIE FABRICANTE`. Peñafiel: `SERIE` vacía | serie no válida | |
| D3 | `CBU` vacío o no está en la lista de clientes válidos | Cliente CBU no encontrado | |
| D4 | `TIPO DE SERVICIO` fuera de `MOVIMIENTOS`+`RUTA` | Tipo de servicio no reconocido | |
| D5 | `LATITUD`/`LONGITUD` vacías o 0 | Coordenadas no válidas | |
| D6 | Solo Peñafiel: `ID CLIENTE` vacío | ID de cliente vacío | |
| D7 | Regla de categoría (`CATEGORIA_GEN`) **comentada/desactivada** en ambos | — | |

### Heineken (`parsers/heineken_parse/business.py`, `config/customers/heineken/reglas_heineken.py`)

| # | Flujo | Regla | Estado |
|---|-------|-------|--------|
| H1 | D2D | Sin `CLIENTE DETALLISTA`; sin `SERIE`; `FALLA` no reconocida; distribuidora no reconocida; `SOLICITUD DE SERVICIO` ≠ `MOVIMIENTO` | |
| H2 | Ruta | Sin `CP`; sin `SERIE`; `TIPO DE MOVIMIENTO` ≠ `REPARACION MERCADO` | |
| H3 | D2D | `FALLA` → servicio: ENTREGA DE ENF=instalación; RETIRO DE ENF / RETIRO POR CAMBIO / CAMBIO DE ENF=retiro enfriador; RETIRO DE MOB=retiro mobiliario | |
| H4 | D2D | Canal → puesto → distribuidora, **solo región Oriente (sucursal 7203)**: Moderno D2362, Punto de venta D2363, Centro de consumo D2364 | |
| H5 | Ambos | Duplicado = serie real (≠ `ASIGNAR SERIE GENERICA`) con caso abierto en Postgres → `OS = DUPLICADO` | |
| H6 | Ruta | Distribuidora fija `500166 \| D1604 \| DIST. CM VALLEJO REHAB. - COACALCO` | |

### Holanda (`parsers/holanda_parse/business.py`, `config/customers/holanda/reglas_holanda.py`)

| # | Regla | Estado |
|---|-------|--------|
| L1 | Rechazo: `CASO2` o `SERIE` vacíos | |
| L2 | Rechazo: `ORIGEN` no reconocido (se infiere del sufijo H/G de `CASO2`) | |
| L3 | Llave del equipo = `CONGELADOR` si viene, si no `SERIE` | |
| L4 | Duplicado intra-lote: gana el `TE` más bajo, luego la fecha más antigua, luego el orden de fila; el resto → `OS = DUPLICADO` | |
| L5 | Duplicado contra histórico: equipo con caso abierto en Postgres → `OS = DUPLICADO` (incluye al ganador del intra-lote) | |
| L6 | Canal siempre `SC \| Sin Canal`, sin importar lo que mande el cliente | |
| L7 | Cada solicitud genera una fila espejo con sufijo `M` en la serie para obtener el id de merma | |

## 4. Pendientes que el propio código reconoce (preguntas para el owner)

- **Heineken:** ¿texto de canal → `cooler_request.canal` y puesto D23xx → `cbu`, está bien? En Ruta, si `NUMERO DE CASO / FOLIO` llega llena, ¿va a `Folio` en lugar de `ORDEN`? ¿Y las demás regiones además de Oriente?
- **Holanda:** mapeos por validar (`SAP`→`Numero_Cliente`, `NOMBRE DEL CLIENTE`→`Nombre_Contacto_PDV`, `Clasificador de caso` siempre vale "Temas de congelador"). ¿`CASO2` se reutiliza o corrige alguna vez? "CONFIRMAR MODELO": ¿contra qué catálogo? Excepción de Yadira Espinosa sin correo real configurado. La columna `MERMA` de la respuesta no se lee ni se guarda.
- **KOF:** ¿qué reglas aplican? Hoy no hay nada.

## 5. Inconsistencias detectadas (a confirmar, no se corrigieron)

- **Duplicados:** Heineken y Holanda los detectan contra Postgres; Danone y Peñafiel no tienen esa regla en `business.py`. ¿Es intencional?
- **`TIPO DE SERVICIO` nulo pasa D4:** `NULL NOT IN (...)` no es verdadero en SQL, así que una fila sin tipo no se rechaza.
- **D5 puede truncar el proceso:** `CAST(LATITUD AS DOUBLE)` falla con texto no numérico (p. ej. "N/A") en vez de rechazar la fila.
- **Rechazadas se borran si el lote queda limpio:** si no hubo rechazos en esta corrida, `solicitudes_rechazadas` se vacía.
- **Peñafiel/Danone repiten ~270 líneas casi idénticas** de reglas; cualquier cambio de regla hay que hacerlo dos veces.

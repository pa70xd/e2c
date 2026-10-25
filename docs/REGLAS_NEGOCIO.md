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

## 6. Cruce contra la wiki (Solkos Wiki → `data/email-to-case/`)

Fuente de verdad del negocio, leída vía el MCP de Emerald (`danone-bonafont.md`, `heineken.md`, `holanda.md`, `penafiel.md`, `kof.md`). Corte de la wiki: 2026-10-15. Aclaración: la wiki tampoco es infalible (varias reglas vienen de sesiones habladas); donde difiere del código, hay que confirmar con REPARE, no asumir que el código está mal.

### Coincide

| Regla | Dónde |
|-------|-------|
| Holanda: espejo de merma con sufijo `M`, canal "sin canal", activo vacío, `CASO2` → folio y ticket | L6, L7 |
| Holanda: duplicado = equipo con caso abierto | L4, L5 |
| Peñafiel sin CBU → se asigna `PENAFIEL` por defecto | `penafiel_parse/reader.py:49` |
| Heineken: precarga D2D = solo movimientos; rutas por el layout Repare ("mantenimiento férguez") | F1 |
| Heineken: series genéricas se generan en Postgres, no en código | `heineken_generar_serie_generica.sql` |
| Canal por defecto `SC \| Sin Canal` (Danone, Peñafiel) | `sabana.py` / `process_data.py` |

### Falta en el código

| Regla de la wiki | Qué encontré |
|------------------|--------------|
| Ruta sin falla → agregar **"no enfría"** (Danone, Heineken, Be-Aware) | Cero ocurrencias en el repo |
| Reubicación: si el cliente manda el par RETIRO+REUBICACION con la misma serie, se toma tal cual; si manda solo la REUBICACION, se generan **dos OS** (serie con `R`) | Solo existe la palabra en listas de tipos; no hay desdoblado ni detección de par |
| Danone: todos los retiros van a `3002 \| RETIRO DE EQUIPO` (`3012` es solo de OXO) | `3002` solo aparece en Heineken |
| Danone y Peñafiel: el **cliente detallista** es obligatorio | Danone solo exige que exista la *columna* `ID CLIENTE`, no que la fila venga llena (Peñafiel sí lo valida, D6) |
| Holanda: el **número de cliente SAP** es obligatorio | Solo se validan `CASO2` y `SERIE` |
| Holanda: excepción de remitente autorizado sin CASO/SAP | `REMITENTES_SIN_DATOS_OBLIGATORIOS` está vacío (falta el correo real) |
| Heineken: "instalación de mobiliario" se crea como **retiro** con serie genérica `MOB…` | `SERVICIOS_D2D` no tiene esa clave: esas filas se rechazan como "FALLA no reconocida" |
| Heineken: número de cliente siempre `5785` | Cero ocurrencias |
| Heineken Ruta: `REPARACION MERCADO` no basta, hay que mirar la falla (Julio, 15-oct) | H2 rechaza todo lo que no diga `REPARACION MERCADO` |
| Almacenes 15/20/21, nunca 44 (todas las instalaciones) | Sin validación; la propia wiki la marca como "todavía no implementable" |
| KOF completo: ~10 formatos, archivos multi-hoja, texto plano en el cuerpo, concatenado de distribuidor (≤18 dígitos), venta de material por palabras clave, "áreas generales" para proyectos especiales | `parsers/kof.py` es un stub |
| Grupo Modelo (pidió Julio pasarlo antes que KOF, 2026-09-29) | No existe en `config/customers/` |

### Contradice

> **Ojo con la severidad:** Danone está en producción. El hallazgo del CBU sale de 13 filas de muestra de mayo; un rechazo con motivo puede ser comportamiento deseado. Tratar estas filas como **hipótesis a validar** contra `solicitudes_rechazadas` en prod (conteo por motivo), no como bugs confirmados. Tampoco está garantizado que este repo (import inicial) sea idéntico a lo desplegado.

| Wiki | Código |
|------|--------|
| El **CBU de Danone no es confiable**: llega como `BNF`/`BONAFONT` (alias), vacío en 2 de 13 filas, y en un layout la columna no existe | `EXPECTED_COLUMNS` exige la columna `CBU` (archivo completo rechazado si falta) y D3 rechaza cada fila con CBU vacío o fuera de la lista |
| Peñafiel: el CBU vacío no importa, se deja `PENAFIEL` por defecto | El default solo se aplica si la **columna** falta; si existe y viene vacía, D3 rechaza la fila |
| Heineken: prefijo de serie genérica `ENF`/`MOB` + `ORI`/`NRT` + fecha + consecutivo | El código usa prefijo `HEI` para enfriadores (la transcripción del 15-oct habla de "mobiliario y Heineken", así que puede ser intencional) |

### Pendientes abiertos en la wiki (sin respuesta)

- Danone: la distribuidora "toma la primera de la lista" cuando hay varias candidatas; REPARE lo dejó como hueco marcado hasta que los clientes manden anexo/puesto de trabajo.
- Peñafiel: "hay que respetar mucho la columna canal" — la regla concreta está en conversación con Julio y no se registró.
- Peñafiel: regla de series genéricas sin documentar (la wiki dice que aplica igual que Heineken, sin detalle).
- Heineken: rutas y movimientos llegan en dos hilos distintos; falta el visto bueno de REPARE.

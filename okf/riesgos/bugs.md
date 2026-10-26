---
type: Known Issues
title: Bugs verificados y reportados
description: Bugs del repo con su estado de verificación. "Verificado" = revisado en el código. "Reportado" = hallazgo de análisis estático, no reproducido.
tags: [bugs, riesgos]
---

# Verificados en código

1. **Regex con `\a`**: `movimientos_danone.py:164-165` y `movimientos_penafiel.py:317-318` usan `\avisos` y `\aviso`. `\a` es BEL en `re`. Nunca matchean.
   * **Estado**: corregido y mergeado en `claude/admiring-lovelace-3oh7g0` (rama `claude/e2c-fix-mecanicos`). En la base: `\bavisos?\b(?!\s+(?:de\s+)?privacidad)` (con lookahead que excluye "aviso de privacidad") en Danone (línea 164) y Penafiel (línea 317). Verificado en la base.
2. **`calcula_modelo` es stub**: `danone_parse/catalog.py:388-401` solo agrega columnas. Modelo, categoría y línea quedan NULL. Las sábanas leen `*_GEN` vacío.
   * **Estado: corregido en parte**, en la rama `claude/e2c-modelos` (`ee6c3a0`, `a8cf448`; sin mergear). `parsers/core/modelos.py` llena `MODELO_GEN`, `CATEGORIA_GEN`, `LINEA_GEN`, `ACTIVO_GEN`, `SERIE_GEN` y una columna nueva `MODELO_GEN_MOTIVO` (`exacto|normalizado|no_en_catalogo|ambiguo|sin_modelo`), sin fuzzy, en Danone y Penafiel (Penafiel usa el catálogo de Danone). Parcial porque: (a) 46 de 803 modelos únicos del catálogo son ambiguos (verificado en `eval/reportes/modelos_ambiguos.md`: 16 FV, 13 CH, 4 EHF entre ENFRIADOR/CONGELADOR y CORTINA DE AIRE, y 3 más) y salen vacíos; (b) los modelos fuera del catálogo salen vacíos en categoría y línea. Correcciones al diagnóstico: las sábanas movimiento/ruta leían `MODELO` crudo, ahora `COALESCE(MODELO_GEN, MODELO)`; el modelo crudo sí se persistía en `cooler_request.modelo`. Nuevo: `eval/cobertura_modelos.py` (solo lectura) mide el porcentaje por motivo y cliente.
   * **Cambio de comportamiento visible (commit `a8cf448`, más reciente que el resumen de la sesión):** el correo de respuesta de Danone y Penafiel agrega al final un párrafo "Modelos sin resolver: ..." si hay modelos sin resolver; si todo resuelve, no cambia. Se regeneraron 5 goldens y 4 fixtures xlsx (ahora con modelos del catálogo), contra la afirmación de la sesión de que los goldens no cambiaron. **Actualización (resumen final de la sesión):** los 5 goldens se actualizaron a propósito; la rama está aprobada por la orquestadora para merge; sin cambios en PostgreSQL; el placeholder `XXXXX` no se indexa (802 modelos indexables de 803 únicos). La sesión da el bug por "corregido"; yo lo mantengo **corregido en parte** mientras 46 modelos salgan vacíos por ambiguos. `eval/cobertura_modelos.py` (porcentaje por motivo y cliente, top 30 de no encontrados) **aún no se ha corrido con datos reales**: es el número que necesita el dev. Punto abierto: Penafiel usa el catálogo de Danone (no tiene propio); la orquestadora lo lleva al usuario. <a id="modelo-categoria-y-linea-no-se-llenan"></a>
3. **`insert_update_cooler` nunca detecta cambios**: `email_update_cooler.sql` no tiene `RETURNING`, así que `execute_query` devuelve `None` y `if updated:` nunca se cumple. Siempre inserta, y puede duplicar `row_number`.
   * **Estado**: corregido y mergeado en `claude/admiring-lovelace-3oh7g0` (rama `claude/e2c-fix-returning`, commits `877f03e`, `dc30f34`). `email_update_cooler.sql` ahora tiene `RETURNING`. **Corrección al diagnóstico**: el duplicado de `row_number` no venía de la falta de `RETURNING`, porque el `NOT EXISTS` por series ya lo frenaba en filas PENDING. Venía de filas ACCEPTED reenviadas con la serie corregida: el UPDATE solo mira PENDING y la serie nueva pasaba el `NOT EXISTS`. Ahora `cooler_request.sql` también bloquea por `request_code` + `row_number`. Además, el `NOT EXISTS` colapsaba dos filas con ambas series vacías; ahora el match por series solo aplica si alguna serie no está vacía.
4. **`update_cooler` no cuenta**: `update_cooler.sql` no tiene `RETURNING`. El contador no sube.
   * **Estado**: corregido y mergeado en `claude/admiring-lovelace-3oh7g0` (rama `claude/e2c-fix-returning`, commits `877f03e`, `dc30f34`). `update_cooler.sql` tiene `RETURNING`; `update_cooler` cuenta con `if result:` y devuelve el total.
5. **Danone `bot.cancelar` no cancela coolers**: `parsers/danone.py:476-484` solo llama `cancel_email_request`. Un outbound posterior reabre la solicitud porque `email_request_update.sql` no excluye CANCELLED.
   * **Estado**: corregido y mergeado en `claude/admiring-lovelace-3oh7g0` (rama `claude/e2c-fix-parsers`). `bot.cancelar` llama a `db.cancel_pending_coolers(request_code)` antes de `cancel_email_request`, igual que Heineken y Holanda. Si la primera falla, la segunda no corre (mismo `try`). **Penafiel tenía el mismo defecto** (`parsers/penafiel.py:468-472`) y también está corregido en la rama (commit `a5bd0fc`), con el mismo riesgo del `try` único.
6. **`detect_direccion` puede ser `None`**: `src/service.py:245` desempaqueta el resultado; `src/email_type.py:215` puede devolver `None`. Revienta sin capturar.
   * **Estado**: corregido y mergeado en `claude/admiring-lovelace-3oh7g0` (rama `claude/e2c-fix-orquestador`). `service.py` loguea sin PII, cierra `duckConn` y retorna `None`. `email_type.py` no se tocó: `detect_direccion` sigue pudiendo devolver `None` (contrato intacto), solo se maneja en el llamador.
7. **`bot.estatus` de Danone**: `data` queda sin asignar si la consulta falla. Lanza `UnboundLocalError`.
   * **Estado**: corregido y mergeado en `claude/admiring-lovelace-3oh7g0` (rama `claude/e2c-fix-parsers`) (commit `2ab001b`), en Danone y Penafiel. `data = None` y, si no hay datos, responde `msj_fail()`. Depende de la versión sin argumentos de `msj_fail` (la segunda definición, `messages.py:331`, que sobrescribe la de la línea 287: ver bug 9 de la orquestadora, `msj_fail` duplicada).
8. **Penafiel `DEBUG == "True"`**: `penafiel.py:230` compara bool con string. Nunca se cumple.
9. **`msj_fail` duplicada**: `messages.py:287` y `messages.py:331`. La segunda sobrescribe.
   * **Estado**: corregido y mergeado en la base (rama `claude/e2c-limpieza`) (`085c4b3`). Queda la versión sin argumentos, la que ya ganaba y la que usa `bot.estatus`.
10. **`form_solicitud.sql` con coma final**: línea 24, antes de `);`. Verificar si se ejecuta.
    * **Estado**: corregido y mergeado en `claude/admiring-lovelace-3oh7g0` (rama `claude/e2c-fix-mecanicos`). Coma quitada de `"OS"`; era la única.

# Reportados, no reproducidos

* **Stopwords antes del regex** (Danone): `convertir_html_a_texto` quita stopwords antes de evaluar patrones. **Reproducido** por el harness (rama `claude/e2c-harness`): "Se realizó la instalación" pasa como propósito válido porque se quita "se" antes de evaluar `IGNORE_REQUESTS`. Falta probar con correos reales.
* **NaN a PostgreSQL**: `send_email_coolers` usa valores crudos en vez de los limpios (`danone.py:248-249`). Mismo patrón en gen y penafiel.
  * **Estado**: verificado y corregido y mergeado en `claude/admiring-lovelace-3oh7g0` (rama `claude/e2c-fix-parsers`). La causa estaba en el repositorio: `send_email_coolers` limpiaba `serie_fabricante` y `serie_dnn_bnf` en variables locales pero pasaba `parametros[...]` crudos al INSERT y al `WHERE NOT EXISTS`. Ahora usa las limpias en `repository/{danone,gen,penafiel}/consultas_postgre.py`. El parser ya limpiaba con `clean_value`.
* **`consulta_link_email`**: 22 placeholders y 21 parámetros. Fallaría con `IndexError`. Sin llamadores.
* **`get_total_coolers`**: devuelve lista pero está anotado como int. Con request inexistente, `TypeError`.
* **Contadores de `email_request_update.sql`**: REJECTED cuenta en total pero no en completed ni failed. Una solicitud puede pasar a COMPLETED con rechazados.
* **`completed_at`**: se reescribe en cada recálculo.
* **Finalizar un cancelado**: `complete_email_request.sql:7` permite completar CANCELLED.
* **Respuestas falsas de éxito**: comandos responden éxito aunque el UPDATE no afecte filas.
* **`update_cooler.sql`**: sin filtro por `row_number`. Serie vacía puede actualizar varias filas.
  * **Estado**: resuelto con un guard de serie vacía (`NULLIF(TRIM(serie),'')`) mergeado en `claude/admiring-lovelace-3oh7g0` (rama `claude/e2c-fix-returning`, commits `877f03e`, `dc30f34`), sin filtrar por `row_number`: el Excel de respuesta no trae `row_number` y derivarlo del orden del df asignaría la OS al equipo equivocado si alguien reordena el archivo.
* **`heineken_cooler_upsert_d2d.sql`**: vuelve a PENDING filas ACCEPTED al reenviar. Sobrescribe OS.
* **`heineken_conciliar_d2d.sql`**: sobrescribe OS de filas ya conciliadas.
* **Traslados en Danone**: `TRASLADO` no está en `DIC_SABANAS_MOV`. Probable rechazo.
* **CBU `PEÑAFIEL`**: pasa validación y no obtiene distribuidora.
* **DIRECCION en Penafiel**: obligatoria en `EXPECTED_COLUMNS`, alias comentados. Columna descartada.
* **Mayúsculas en filtros**: `TIPO DE SERVICIO IN (...)` exacto, pero la validación usa `UPPER`. "Instalación" en minúscula pasa validación y queda fuera de sábana.
* **Heineken cambios**: `RETIRO POR CAMBIO` y `CAMBIO DE ENF` generan solo retiro.
* **Holanda outbound**: no aplica regla 403. Cuenta todas las OS como con OS.
* **Holanda `business.py:71`**: devuelve `rechazadas == 0`, semántica invertida.
* **Escritura antes de responder**: `holanda.py:144-148` retorna `None` tras guardar. Mismo patrón en Danone y Penafiel.
* **Mensaje como dict**: Heineken y Holanda devuelven dict, Graph espera str.
* **`.xlsm` mal alineado** en Danone y Holanda: detectado como Excel pero el lector solo acepta `.xlsx` y `.xls`.
* **Danone `failed_coolers`** siempre 0.
* **Penafiel sembrado de columnas**: `penafiel_parse/reader.py:52-78` siembra vacío en columnas obligatorias. Las guardas nunca reportan faltantes. Mismo patrón en Holanda.
* **Duplicados sin detectar**: Danone y Penafiel solo deduplican por `mail.id`. Heineken sin dedupe intra-lote.
* **Teléfonos inconsistentes**: qué columna va a qué campo cambia entre sabana y process_data.
* **Coordenadas**: `CAST(LATITUD AS DOUBLE)` sin control. Un valor no numérico aborta.
* **Excepciones de DB sin capturar** en distribuidora de gen y Danone.
* **Descarte silencioso** de adjuntos cuando cambia la estructura (`unir_tablas`).
* **PII en logs**: texto completo del correo en `gen_parse/utils.py:31` y `danone_parse/utils.py:30`.
* **`penafiel.py:60`**: cuerpo y asunto concatenados sin separador.
* **Rutas relativas al cwd**: `config/email_index.json` y "Documentos_Adjuntos".
* **Holanda `pd.read_excel`**: toma primera hoja aunque esté oculta.
* **Heineken `MAX(row_number)`**: sin transacción. Concurrencia puede repetir.
* **Riesgo de la corrección de `\a`→`\b`**: `aviso` ahora sí coincide en `MOVEMENTS`; el harness corroboró que sin guarda un pie "Aviso de privacidad" generaba movimientos falsos. Mitigado en la base con el lookahead `(?!\s+(?:de\s+)?privacidad)`. Otros pies que contengan "aviso" no se probaron.
* **Hallazgos del análisis de 21 correos reales** (2026-10-26, ver [correos reales](../pruebas/correos-reales.md); cifras de la orquestadora, no verificadas por mí salvo lo indicado):
  * **Holanda descarta todo** si el asunto lleva fecha: `es_asunto_holanda` exigía el asunto exacto (`parsers/holanda.py:70`). Incluye la conciliación de OS. **Corregido en la rama `claude/e2c-fix-holanda-indice`, sin mergear** (`330763f`): acepta fecha o sufijo numérico; verifiqué ejecutándola ("RE: Casos REPARE 04052026" sí; "Casos REPARE 04052026 urgente" y "Fwd: algo Casos REPARE" no). Sigue abierto: el lector de Holanda no acepta `.xlsm` (solo `.xlsx`/`.xls`, `reader.py:19` según la sesión).
  * `config/email_index.json` incluye un buzón personal (verificado) y no mapea Imbera, oxxo, oxogar, torrey ni kof: 14 de 21 correos nunca entran. Decisión de alcance pendiente con el usuario.
  * La etapa sale solo del prefijo "RE:", sin `In-Reply-To` (verificado).
  * `detect_direccion` mira solo el `To:` (verificado) y confunde correos internos de REPARE.
  * Excel (**corregido en parte** en la rama `claude/e2c-lector-excel`, sin mergear: el lector común acepta `.ods`/`.xlsm` y los lectores actuales ganan esas extensiones; una `.ods` en los lectores actuales no filtra hojas ocultas, y `.xls` necesita `xlrd`, que no está en `requirements.txt`; ver [lector](../parsers/lector.md)): `.ods` no se aceptaba, Holanda no aceptaba `.xlsm`, encabezados de Imbera de 2 a 4 filas, hojas ocultas de KOF no se leen.
  * El outbound solo concilia por Excel: las OS en texto se pierden.
  * `redact()` dejó pasar nombres, direcciones, coordenadas, un URL de mapa, correos y montos: **bloqueante** para sombra y haiku con correos reales.
* **Hallazgos del harness** (rama `claude/e2c-harness`, sin corregir; ver [harness](../pruebas/harness.md)):
  * Corrobora el riesgo de `\baviso\b`: con el parche hipotético, un pie "Aviso de privacidad" convierte correos sin solicitud en movimientos. Un test documenta el estado actual.
  * `bot.global`: `process_email_request_global` revienta si `created_at` trae `tzinfo` (openpyxl no admite datetimes con zona). Si Postgres devuelve `timestamptz`, en producción cae al `except` y responde sin archivo. No verificado con datos reales.
  * Danone: un `bot.*` desconocido (p. ej. `bot.inexistente`) no se detecta como comando; el `case _` de `parse` es inalcanzable y no se responde.
  * Penafiel: una fila rechazada por SERIE vacía queda en `cooler_request` con OS "[RECHAZADO]..." pero no se pinta en el Excel devuelto (la de ID vacío sí). Observado, no investigado.
  * Las rechazadas se persisten como coolers PENDING con OS "[RECHAZADO] ..." y `total_coolers` también las cuenta.
  * Listas `DISTINCT` sin `ORDER BY` (llaves de Holanda, series de Heineken) cambian de orden entre corridas.
* **Hallazgos nuevos de fix-parsers** (sin corregir):
  * `bot.estatus` de Danone y Penafiel: el `print` de error dice "No se logro cancelar" (copy-paste).
  * Una serie numérica leída como float se guarda como `'123.0'` y puede romper el dedupe con `COALESCE` contra la misma serie guardada como `'123'`.
  * `gen` `send_email_coolers` y `gen_parse/process_data.prepare_data_cooler` no tienen llamadores.
  * Al importar `main`, la conexión apunta a PRODUCCIÓN por defecto (log `[BASEDATOS] dirigido a -> PRODUCCIÓN`). Verificado: sin `DEBUG=true` usa PRODUCCIÓN. Ver [despliegue](../deploy/despliegue.md).
* **Outbound de Danone `bot.cancelar`**: ver verificado 5.

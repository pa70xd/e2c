---
type: Known Issues
title: Bugs verificados y reportados
description: Bugs del repo con su estado de verificación. "Verificado" = revisado en el código. "Reportado" = hallazgo de análisis estático, no reproducido.
tags: [bugs, riesgos]
---

# Verificados en código

1. **Regex con `\a`**: `movimientos_danone.py:164-165` y `movimientos_penafiel.py:317-318` usan `\avisos` y `\aviso`. `\a` es BEL en `re`. Nunca matchean.
2. **`calcula_modelo` es stub**: `danone_parse/catalog.py:388-401` solo agrega columnas. Modelo, categoría y línea quedan NULL. Las sábanas leen `*_GEN` vacío. <a id="modelo-categoria-y-linea-no-se-llenan"></a>
3. **`insert_update_cooler` nunca detecta cambios**: `email_update_cooler.sql` no tiene `RETURNING`, así que `execute_query` devuelve `None` y `if updated:` nunca se cumple. Siempre inserta, y puede duplicar `row_number`.
4. **`update_cooler` no cuenta**: `update_cooler.sql` no tiene `RETURNING`. El contador no sube.
5. **Danone `bot.cancelar` no cancela coolers**: `parsers/danone.py:476-484` solo llama `cancel_email_request`. Un outbound posterior reabre la solicitud porque `email_request_update.sql` no excluye CANCELLED.
6. **`detect_direccion` puede ser `None`**: `src/service.py:245` desempaqueta el resultado; `src/email_type.py:215` puede devolver `None`. Revienta sin capturar.
   * **Estado**: corregido en rama `claude/e2c-fix-orquestador`, sin mergear. `service.py` loguea sin PII, cierra `duckConn` y retorna `None`. `email_type.py` no se tocó.
7. **`bot.estatus` de Danone**: `data` queda sin asignar si la consulta falla. Lanza `UnboundLocalError`.
8. **Penafiel `DEBUG == "True"`**: `penafiel.py:230` compara bool con string. Nunca se cumple.
9. **`msj_fail` duplicada**: `messages.py:287` y `messages.py:331`. La segunda sobrescribe.
10. **`form_solicitud.sql` con coma final**: línea 24, antes de `);`. Verificar si se ejecuta.

# Reportados, no reproducidos

* **Stopwords antes del regex** (Danone): `convertir_html_a_texto` quita stopwords antes de evaluar patrones. Algunos patrones obligatorios contienen stopwords. Falsos negativos de propósito. Probar con correos reales.
* **NaN a PostgreSQL**: `send_email_coolers` usa valores crudos en vez de los limpios (`danone.py:248-249`). Mismo patrón en gen y penafiel.
* **`consulta_link_email`**: 22 placeholders y 21 parámetros. Fallaría con `IndexError`. Sin llamadores.
* **`get_total_coolers`**: devuelve lista pero está anotado como int. Con request inexistente, `TypeError`.
* **Contadores de `email_request_update.sql`**: REJECTED cuenta en total pero no en completed ni failed. Una solicitud puede pasar a COMPLETED con rechazados.
* **`completed_at`**: se reescribe en cada recálculo.
* **Finalizar un cancelado**: `complete_email_request.sql:7` permite completar CANCELLED.
* **Respuestas falsas de éxito**: comandos responden éxito aunque el UPDATE no afecte filas.
* **`update_cooler.sql`**: sin filtro por `row_number`. Serie vacía puede actualizar varias filas.
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
* **Outbound de Danone `bot.cancelar`**: ver verificado 5.

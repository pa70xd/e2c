# Evaluador del clasificador (Fase 3)

Mide gate y extract de cada proveedor (`regex`, `haiku`) ANTES de activarlo.

```bash
python eval/run_eval.py --provider regex --set eval/sets/sintetico.jsonl
ANTHROPIC_API_KEY=... python eval/run_eval.py --provider haiku --set eval/sets/sintetico.jsonl
```

* Sin `ANTHROPIC_API_KEY`, `--provider haiku` lo avisa y sale con código 0 sin llamar a nada.
* Sale con código 1 si la precisión del gate es menor que `--umbral` (default **0.95**, fijado por el usuario).
* `--json ruta` guarda el resumen completo.
* Cada caso pasa siempre por `classifier.redact` y luego por `classifier.decidir` (misma ruta que producción, con validación y caída a regex).
* Costo de haiku: define `EVAL_PRICE_IN` y `EVAL_PRICE_OUT` (USD por millón de tokens). Sin ellas el reporte dice "costo: no configurado"; no hay precios fijos en el código.
* Los reportes solo imprimen ids de caso, nunca texto de correos.

Formato del set: [`schema.md`](schema.md). Set inventado: `sets/sintetico.jsonl`.

## Set real (fuera del repo)

`eval/sets/real/` está en `.gitignore`: los casos reales no se suben. Procedimiento:

1. **Redactar.** Pasa cada correo por `classifier.redact` (asunto y cuerpo, conservando las series que ya estén en `cooler_request`). No guardes el original en esta carpeta.
2. **Revisar a mano.** Lee el texto redactado completo: busca nombres de personas o tiendas, direcciones, teléfonos, correos, RFC, folios internos o lo que `redact` no cubra (ver sus limitaciones). Edita lo que quede; si un caso no se puede limpiar, descártalo.
3. **Etiquetar.** Solo después de revisar, escribe `esperado` (`es_os`, `tipo_evento`, `filas`) y, si es un hilo, `thread_ctx` con series y estados. Usa `"fuente": "real"`.
4. **Guardar** como `eval/sets/real/<nombre>.jsonl` y correr el evaluador con `--set` apuntando ahí.

Nunca pegues correos reales en issues, PRs ni chats.

## Archivos

* `run_eval.py`: carga, ejecución, reporte y veredicto.
* `metrics.py`: cálculo de métricas (funciones puras, con pruebas en `tests/unit_eval/`).
* `smoke_haiku.py`: smoke manual de otra sesión (una llamada real por operación).

## Backfill: set real desde los buzones históricos (`backfill.py`)

Arma un set real con etiquetas automáticas: si un correo generó filas en la base, era una OS y se procesó bien. **Solo lectura**: Graph solo con GET y PostgreSQL solo con SELECT dentro de `SET TRANSACTION READ ONLY` (cualquier consulta que no sea SELECT aborta el script). No procesa correos, no llama a parsers ni a `review/`.

Comando (con TUS credenciales, las variables de siempre: `CLIENT_ID`, `CLIENT_SECRET`, `TENANT_ID`, `SECRET_PG_ACC`, `DB_HOST`, `DB_NAME`, `DB_PORT`):

```bash
python eval/backfill.py --tablas qa --desde 2026-07-01 --hasta 2026-10-26 --maximo 100
```

Opciones: `--buzones` (default: los de `config/email_index.json`), `--desde`/`--hasta` (YYYY-MM-DD; default últimos 90 días), `--maximo` por buzón (default 100; con el corte dentro del rango se reparte mitad ajuste y mitad examen), `--corte` (desde esa fecha el split es `examen`; default últimos 30 días), `--salida` (default `eval/sets/real/backfill_<fecha>.jsonl`, ya en `.gitignore`), `--tablas qa|prod` (default `qa`).

**`--tablas prod` exige `--confirmo-solo-lectura`.** Úsalo solo con un usuario de base de solo lectura, si existe. El script ya fuerza READ ONLY, pero un usuario sin permisos de escritura es la garantía real. `qa` lee `*_qa`, que puede tener poca historia.

**Candado de redacción:** el script aborta (código 5) si `classifier.redact.REDACT_VERSION` es menor que 2 (o no existe): el `redact` v1 deja escapar nombres y direcciones en correos reales. `--permitir-redact-v1` lo salta y es solo para pruebas.

Salida:

* `backfill_<fecha>.jsonl`: todos los casos, en el formato de `schema.md` más `split`, `etiqueta_fuente`, `evidencia` (filas generadas y sus estados), `adjuntos` (nombre, tipo, hojas, filas, encabezados; nunca el contenido) e `ids` en hash. Asunto, cuerpo, nombres de adjunto y encabezados pasan por `classifier.redact` antes de escribirse.
* `backfill_<fecha>_revision.jsonl`: los casos sin evidencia o sin tipo de evento, para revisión humana.

Etiquetas: `historico` si la base lo prueba (filas generadas → `nueva_solicitud`; en un hilo, filas nuevas/cambiadas/canceladas dentro de los 10 min del correo → `agregar_filas`/`modificar_filas`/`cancelar_filas`; correo de REPARE con OS adjuntas → `categoria: "cierre"`, que no es un tipo del clasificador, va con `tipo_evento: null`). `sin_evidencia` con `es_os: null` si no hay rastro: **nunca se asume `no_os`**. Los correos del bot se omiten.

Evaluar:

```bash
python eval/run_eval.py --provider regex --set eval/sets/real/backfill_<fecha>.jsonl --solo-etiquetados --split examen
```

`--solo-etiquetados` ignora los casos con `es_os` o `tipo_evento` null; `--split ajuste|examen` filtra por el campo `split`. Ajusta con `ajuste` y mide con `examen`; nunca midas con los mismos correos con que ajustaste.

Qué revisar a mano:

1. **Todo `_revision.jsonl`**: un correo sin rastro pudo ser una OS que falló al parsear, o ruido. Etiquétalo a mano (o descártalo) antes de usarlo.
2. **PII residual**: lee los textos redactados (los marcados `revisar_pii` primero); `redact` no cubre nombres sin despedida ni etiqueta. Nunca pegues el set en issues, PRs ni chats.
3. **Hilos**: `thread_ctx` se reconstruye desde el estado actual de la base (`ctx_aproximado: true`); lo que cambió después del correo no se puede deshacer.
4. **Reloj de la base**: `cooler_request` y `emails_log` pueden usar husos distintos; el script calibra la diferencia con el primer correo de cada solicitud y, si no puede, deja el caso sin evidencia. Si ves muchos hilos en `sin_evidencia` con `sin_calibracion_de_reloj`, revisa los husos.
5. **Falsos "historico"**: filas aceptadas por un humano o cargadas por otra vía también generan filas; revisa una muestra de `nueva_solicitud`.
6. **Hash de ids**: para ubicar un correo en el buzón, `python eval/backfill.py --hash <id_de_graph>` y compara con `ids.mensaje`.

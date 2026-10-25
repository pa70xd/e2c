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

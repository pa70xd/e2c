# Formato del set de evaluación

Un archivo JSONL: un caso por línea, UTF-8. `eval/run_eval.py` lo valida al cargar
(campos obligatorios, enums de `classifier/contracts.py`, ids únicos).

```json
{
  "id": "rep-can-01",
  "fuente": "sintetico",
  "etapa": "reply",
  "cliente": "danone",
  "direccion": "inbound",
  "asunto": "Re: Solicitud de servicio",
  "cuerpo": "Cancelen la primera y la tercera. [FIRMA]",
  "thread_ctx": {
    "filas": [
      {"row_number": 1, "serie_fabricante": "SF-1001", "serie_dnn_bnf": null, "status": "PENDING"}
    ],
    "decisiones": [{"tipo_evento": "nueva_solicitud", "es_os": true, "proveedor": "regex"}]
  },
  "esperado": {
    "es_os": true,
    "tipo_evento": "cancelar_filas",
    "filas": [{"accion": "cancelar", "row_number": 1}]
  },
  "nota": "opcional, texto libre"
}
```

## Campos

| Campo | Obligatorio | Descripción |
|---|---|---|
| `id` | sí | Único en el set. |
| `fuente` | sí | `sintetico` (inventado) o `real` (correo real ya redactado). |
| `etapa` | sí | `init` (correo nuevo) o `reply` (mensaje de hilo). |
| `cliente` | no | Cliente del correo (`danone`, `penafiel`, `holanda`, `heineken`). El gate `regex` decide distinto por cliente en `init`. Extensión al formato mínimo. |
| `direccion` | no | `inbound`, `outbound`, `reply_to_bot` o `bot`. |
| `asunto` | no | Asunto, ya redactado. |
| `cuerpo` | sí | Cuerpo, ya redactado. El evaluador lo redacta otra vez antes de cualquier proveedor. |
| `thread_ctx.filas` | no | Filas ya guardadas: `row_number`, `serie_fabricante`, `serie_dnn_bnf`, `status` (`PENDING`, `ACCEPTED`, `CANCELLED`, `REJECTED`). Ausente o `null` = filas no cargadas; `[]` = la solicitud no tiene filas. |
| `thread_ctx.decisiones` | no | Decisiones previas del hilo (`tipo_evento`, `es_os`, `proveedor`). |
| `esperado.es_os` | sí | Debe ser coherente con `tipo_evento`: `false` solo con `no_os` y `duplicado`. |
| `esperado.tipo_evento` | sí | Uno de `TIPOS_EVENTO`. |
| `esperado.filas` | no | Filas que el texto pide crear, cambiar o cancelar. Vacío si el correo no lleva filas. |
| `nota` | no | Por qué el caso es difícil. No se usa al evaluar. |

## Filas esperadas

Cada fila lleva `accion` (`agregar`, `modificar`, `cancelar`) y `row_number`
(`null` para `agregar`; el número de la fila guardada para `modificar` y `cancelar`).

Las series (`serie_fabricante`, `serie_dnn_bnf`) son opcionales y **solo se comparan
si la clave está en la etiqueta** (con `null` también cuenta: se exige que la fila
extraída no traiga serie). Etiqueta las series cuando el correo las dicta de forma
explícita y no hay ambigüedad (altas); para `modificar`/`cancelar` por referencia
("la segunda fila") normalmente basta `accion` + `row_number`.

Una fila predicha acierta si coincide en acción, `row_number` y las series
etiquetadas (sin distinguir mayúsculas ni espacios en las series).

## Reglas de la etiqueta

* `modificar` o `cancelar` sobre una fila `ACCEPTED` se etiqueta igual que sobre una
  `PENDING`: el gate y el extract no deciden la revisión humana, esa regla es de
  `classifier.validate.separar_revision`.
* Firma, "Aviso de privacidad", agradecimientos y texto citado de otro correo no son
  un pedido. Un pedido real que va antes de la firma sí lo es.
* Un reenvío cuyas series ya están en el hilo es `duplicado`; el reenvío de un pedido
  nuevo es `nueva_solicitud`.
* Si la serie citada no existe en el hilo, no hay fila a la cual referirse: `filas: []`.

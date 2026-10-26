---
type: Module
title: Redacción de PII (classifier/redact.py)
description: Función redact() que quita datos personales del texto de un correo antes de enviarlo a cualquier proveedor externo (LLM). Mergeado en claude/admiring-lovelace-3oh7g0.
tags: [classifier, redact, pii, fase-3]
---

# Estado

Rama `claude/e2c-redact` (commit `0d8fc00`), **mergeada en la base** `claude/admiring-lovelace-3oh7g0`. Verificado en la rama: `classifier/redact.py` existe; `python -m pytest -q` → 562 passed, 24 skipped, 1 xfailed (base 448/24/1); `tests/unit_classifier/test_redact.py` (114 pruebas sintéticas con `example.com`, incluye fuzz de idempotencia, según la sesión).

# API

`redact(text: str, conservar: Iterable[str] = ()) -> str`. `conservar` son tokens exactos (p. ej. las series ya guardadas en `thread_ctx.filas`) que no se redactan; lo añadió la integración (`281fa4a`). **Obligatoria antes de cualquier proveedor externo (LLM).** Solo stdlib (`re`, `unicodedata`). Idempotente: en una prueba mía con texto sintético, `redact(redact(t)) == redact(t)`.

# Qué redacta

* `[CORREO]`, incluido ofuscado ("x [at] y [dot] com", `&#64;`, `＠`).
* `[TELEFONO]`: 10 dígitos, prefijos +52/52/521/044/01, separadores, extensión; 8 dígitos solo con etiqueta Tel/Cel/WhatsApp.
* `[FIRMA]`: bloque tras una despedida (Saludos, Atentamente, Atte., Quedo atento/a, Gracias, Slds, Cordialmente, Best regards...), "--", "Enviado desde mi...", y pies legales (Aviso de privacidad, "Este correo es confidencial...").
* `[ID]`: RFC/CURP con fecha AAMMDD válida o etiquetados, nombre en la línea de despedida, nombre antes de `<correo>`, cabeceras De/Para/Cc, "Contacto:/Responsable:/Solicitante:".

# redact v2 (rama `claude/e2c-redact-v2`, sin mergear)

Commit `ae4da5e`. Verificado en la rama: `pytest -q` → **993 passed, 48 skipped, 1 xfailed**; `eval/run_eval.py --provider regex` sobre `sintetico.jsonl` sin cambios (gate 0.7419); y una prueba mía con texto inventado: cabeceras De/Para, saludo con nombre, firma sin despedida conocida (nombre en mayúsculas + cargo + Cel), coordenadas, URL de mapa y monto quedan redactados, y folio, serie y modelo intactos; idempotente.

Amplía `redact()` con los patrones F1-F9 (según la sesión):

* Nombres en cabeceras De/Para/CC (minúsculas, comillas, "Apellido, Nombre", línea siguiente, mitad de línea), "Nombre [mailto:]", "El … Nombre escribió:".
* Correos con espacios; campos etiquetados (se redacta el valor, no la etiqueta); tablas con barras/tabuladores y aplanadas (N encabezados + N valores).
* Coordenadas y URLs de mapas; firmas sin despedida conocida; saludos con nombre; montos.
* Marcadores nuevos: `[UBICACION]`, `[MONTO]`, `[DIRECCION]`. Corrige el falso positivo "Atención: El dominio … va a …" → `[ID]`.
* API igual: `redact(text, conservar=())`, solo stdlib, idempotente.

**Criterios nuevos:** no se tocan folios, tickets, series, IDs tipo `IMB-070526_4960`, modelos, tipos de servicio, cadenas (OXXO/Jumex/KOF), razones sociales ni valores genéricos. Un nombre de tienda con nombre de persona se conserva como dato del punto de venta, pero se redacta tras etiqueta de persona, saludo o firma. "Dirección:"/"Domicilio:" sin calificar y las líneas de punto de venta **no** se redactan: solo envío, entrega, garantía, facturación, fiscal, "ubicada en" y columnas calle/colonia/CP.

**Límites (de la sesión):** nombres sin contexto siguen sin detectarse; tablas aplanadas de una sola fila.

> **El bloqueo sigue vigente.** La sesión aún no re-probó `redact` v2 con la batería real de los 21 correos dentro del contenedor, y yo no los tengo. Hasta que se haga y se mergee, no activar `CLASSIFIER_SHADOW` ni haiku con correos reales. Con una muestra de 21, además, "0 fugas" no prueba cobertura general: la redacción por patrones puede dejar pasar nombres sin contexto.

# Qué NO redacta (v1, sigue valiendo en v2 salvo lo indicado arriba)

Folios, series (p. ej. `ABC123456`, `E64190100186`, 12/18 dígitos), modelos (p. ej. `FVC14-E1`), tipo de servicio, acciones (alta/baja/retiro/cancelar/cambio), direcciones de punto de venta, asunto, fechas.

# Serie vs. teléfono (criterio)

1. Un token con letras nunca es teléfono.
2. Corridas pegadas de 11+ dígitos no son teléfono; 52/521 sin "+" solo con formato o palabra Tel.
3. 10 dígitos exactos son teléfono, salvo que la última palabra clave de la misma línea antes del número sea serie/folio/ticket/activo/modelo/equipo/s/n sin "Tel/Cel/WhatsApp" posterior. Un encabezado "Series:" en la línea previa extiende el contexto a la lista.
4. Sin contexto y con 10 dígitos, se redacta (privacidad primero): una tabla de series de 10 dígitos sin etiqueta perdería datos.

# Fin del bloque de firma

Frontera de hilo ("El… escribió:", "De:", "Enviado:", "----Original"), cambio de nivel de `>`, línea con palabras de acción/equipo/serie/folio/dirección de PDV, token tipo serie, o línea de más de 100 caracteres. Los pies legales llegan hasta la frontera.

# Límites conocidos

* Nombres sin despedida ni etiqueta no se detectan (haría falta un modelo).
* Una despedida al final de una línea de prosa solo abre bloque si la línea siguiente es un nombre.
* Consecuencia del criterio 4: una serie de 10 dígitos sin contexto se redacta como teléfono, lo que quita datos útiles al clasificador. No está medido cuánto afecta a la precisión.

Ver [decisiones](../riesgos/decisiones.md) para el umbral de activación de la Fase 3.

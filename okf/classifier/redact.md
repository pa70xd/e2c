---
type: Module
title: Redacción de PII (classifier/redact.py)
description: Función redact() que quita datos personales del texto de un correo antes de enviarlo a cualquier proveedor externo (LLM). Mergeado en claude/admiring-lovelace-3oh7g0 (v1). La v2 está en la rama claude/e2c-redact-v2, sin mergear.
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

## Resultado final (resumen final de la sesión, commit `c15543e`)

Rama aprobada por la orquestadora para merge; **aún no mergeada** (lo verifiqué: la base no la contiene). Verificado en la rama: `REDACT_VERSION = 2` (candado), `redact` itera a punto fijo (máx. 5), `pytest -q` → **1062 passed, 48 skipped, 1 xfailed**.

**Medición sobre los 21 correos reales** (hecha por la sesión dentro del contenedor; yo no tengo los correos): v1 → v2 — nombres 53 → 2; direcciones 7 → 0; coordenadas 6 → 0 útiles (queda 1 truncada a 2 decimales, "aceptable"); montos 3 → 0; correos 2 → 0; URL de mapa 1 → 0; teléfonos 0.

**Límites conocidos — los 2 nombres que siguen pasando:**

1. "NOMBRE APELLIDO" solo en una línea entre líneas en blanco, sin etiqueta, cargo, saludo ni firma. **Lo reproduje** con texto inventado: queda sin redactar. No se detecta sin un modelo.
2. Valor de columna de contacto en una tabla aplanada desalineada por una celda vacía: el redactor no redacta por posición cuando el bloque no cuadra.
3. En general, nombres sin ningún contexto siguen sin detectarse.

**Candado `REDACT_VERSION`:** el código exige `REDACT_VERSION >= 2` para que corra un proveedor externo o la sombra ([runbook](../deploy/runbook-lunes.md)). **Al mergear esta rama el candado se abre solo**, aunque quedan 2 nombres de 21 correos sin redactar (y una muestra de 21 no prueba cobertura general). Es una decisión de riesgo del usuario: aceptar esa fuga residual antes de mandar correos reales a un proveedor externo, o exigir revisión manual/otra capa.

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

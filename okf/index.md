---
okf_version: "0.2"
---

# e2c — Email to Case

Bundle OKF del repositorio `e2c`: backend FastAPI que recibe correos de clientes con Excel adjunto y los convierte en solicitudes de servicio para coolers (Imbera / REPARE).

## Entrada

* [Visión general](overview.md) - qué hace el repo, stack y mapa de carpetas.
* [Despliegue y variables de entorno](deploy/despliegue.md) - Docker, Cloud Run, env vars.
* [Runbook del lunes](deploy/runbook-lunes.md) - pruebas del dev con sus credenciales: DEBUG, pytest, Graph y PostgreSQL.

## Flujos

* [Revisión por hilo (flujo)](flows/revision-por-hilo.md) - qué se aplica y qué va a revisión humana cuando un hilo pide cambios.
* [Recepción de correo](flows/recepcion-correo.md) - desde la notificación de Graph hasta el procesamiento.
* [Solicitud inicial](flows/solicitud-inicial.md) - correo nuevo con Excel: parseo, validación, persistencia y respuesta.
* [Respuesta y comandos del bot](flows/respuesta-y-comandos.md) - hilos, outbound de REPARE, `bot.*`.

## Módulos del orquestador

* [handler y main](services/handler.md) - endpoints HTTP.
* [service (orquestador)](services/service.md) - `processMail`.
* [email_type (clasificación)](services/email-type.md) - validación, cliente, dirección, duplicados.
* [excel_ingestion](services/excel-ingestion.md) - plantillas y validaciones x14.
* [Código muerto del orquestador](services/codigo-muerto.md) - attachments.py, service_request.py, etc.

## Parsers

* [Base gen_parse](parsers/gen-base.md) - librería compartida.
* [Lector común de adjuntos](parsers/lector.md) - `leer_adjunto`: encabezado por vocabulario, hojas ocultas, `.ods`/`.xlsm` (rama `claude/e2c-lector-excel`, sin mergear).
* [Danone](parsers/danone.md)
* [Penafiel](parsers/penafiel.md)
* [Holanda](parsers/holanda.md)
* [Heineken](parsers/heineken.md)
* [KOF (stub)](parsers/kof.md)

## Clientes

* [Índice de clientes y buzones](clients/index.md)
* [Reglas de negocio por cliente](clients/reglas-por-cliente.md)

## Datos

* [Capa de repositorio](data/capa-repositorio.md) - funciones, SQL, patrón de conexión.
* [Modelo de datos inferido](data/modelo-datos.md) - tablas, estados y transiciones.
* [Catálogos y archivos de datos](data/catalogos.md) - distribuidoras, modelos, CSV de prueba.

## Infraestructura

* [Microsoft Graph](infrastructure/graph-api.md)
* [PostgreSQL y Secret Manager](infrastructure/postgres.md)
* [Tableau](infrastructure/tableau.md)
* [Geocodificación Google](infrastructure/geocoding.md)
* [Suscripciones Graph (script manual)](infrastructure/subscriptions.md)

## Configuración compartida

* [config_general](config/config-general.md) - mensajes, palabras reservadas, stopwords.

## Clasificador (Fase 3)

* [Revisión por hilo](classifier/revision.md) - aplica cambios en filas PENDING y manda el resto a revisión humana por correo (mergeado en la base).
* [Núcleo del clasificador](classifier/core.md) - contratos, validación, registro, proveedor regex y gate en el flujo (mergeado en la base).
* [Modo sombra](classifier/sombra.md) - segundo gate en paralelo que solo registra (rama `claude/e2c-sombra`, sin mergear; bloqueado hasta `redact-v2`).
* [Proveedor Haiku](classifier/provider-haiku.md) - `gate()` y `extract()` con Claude Haiku 5.5, opcional (mergeado en la base).
* [Redacción de PII](classifier/redact.md) - `redact()`, obligatoria antes de cualquier proveedor externo (mergeado en la base).

## Pruebas

* [Análisis de 21 correos reales](pruebas/correos-reales.md) - hallazgos redactados: alcance de buzones, bugs de Holanda y de dirección/etapa, `redact()` insuficiente.
* [Evaluación del clasificador](pruebas/evaluacion.md) - gate y extract por proveedor contra el umbral 0.95; regex 0.7419, haiku sin medir (mergeado en la base).
* [Harness de pruebas offline](pruebas/harness.md) - pytest sin red, goldens y xfail de bugs conocidos (mergeado en `claude/admiring-lovelace-3oh7g0`).

## Riesgos y pendientes

* [Bugs verificados y reportados](riesgos/bugs.md)
* [Seguridad](riesgos/seguridad.md)
* [Deuda técnica](riesgos/deuda-tecnica.md)
* [Preguntas abiertas de negocio](riesgos/preguntas-abiertas.md)
* [Decisiones del proyecto](riesgos/decisiones.md) - umbral de la Fase 3, filas ACCEPTED, reglas de fase.

## Historial

* [log.md](log.md)

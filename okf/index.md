---
okf_version: "0.2"
---

# e2c — Email to Case

Bundle OKF del repositorio `e2c`: backend FastAPI que recibe correos de clientes con Excel adjunto y los convierte en solicitudes de servicio para coolers (Imbera / REPARE).

## Entrada

* [Visión general](overview.md) - qué hace el repo, stack y mapa de carpetas.
* [Despliegue y variables de entorno](deploy/despliegue.md) - Docker, Cloud Run, env vars.

## Flujos

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

## Riesgos y pendientes

* [Bugs verificados y reportados](riesgos/bugs.md)
* [Seguridad](riesgos/seguridad.md)
* [Deuda técnica](riesgos/deuda-tecnica.md)
* [Preguntas abiertas de negocio](riesgos/preguntas-abiertas.md)

## Historial

* [log.md](log.md)

---
type: Repository
title: e2c — Email to Case
description: Backend FastAPI que convierte correos con Excel de clientes (Danone, Penafiel, Holanda, Heineken) en solicitudes de servicio de coolers, con respuesta automática por correo.
resource: https://github.com/pa70xd/e2c
tags: [backend, fastapi, email, coolers, imbera, repare]
---

# Qué hace

1. Microsoft Graph notifica un correo nuevo en un buzón de cliente.
2. El servicio descarga el mensaje, lo clasifica (inicial, respuesta, comando del bot, outbound de REPARE) y detecta el cliente.
3. Si es una solicitud inicial, parsea el Excel adjunto con DuckDB, valida reglas de negocio y guarda en PostgreSQL.
4. Responde al correo con tres Excel: sábana de movimientos, sábana de rutas y solicitud.
5. Si llega una respuesta con Excel actualizado (outbound de REPARE), concilia las OS y responde con el estatus.

# Stack

* Python con FastAPI (`main.py`), desplegado con uvicorn en Docker (`python:3.14`, puerto 8080).
* DuckDB en memoria para leer y unir Excel.
* PostgreSQL (psycopg2) con credenciales desde GCP Secret Manager.
* Microsoft Graph (msal, msgraph-sdk) para leer y responder correos.
* Tableau (VizQL) para lookups de modelos y puntos de venta.
* Google Geocoding para coordenadas.

# Mapa de carpetas

| Carpeta | Contenido |
|---|---|
| `main.py`, `src/` | App FastAPI, endpoints, orquestador, clasificación de correos, ingesta de Excel |
| `parsers/` | Un parser por cliente y una librería base `gen_parse` |
| `repository/` | Acceso a PostgreSQL y SQL por cliente |
| `infrastructure/` | Graph, PostgreSQL, Tableau, geocodificación, DuckDB |
| `models/` | Modelos de datos (pydantic y registro de email) |
| `config/` | Reglas, columnas, catálogos y mensajes por cliente y generales |
| `excel_templates/` | Plantillas Excel para las respuestas |
| `subscriptions.py` | Script manual para crear, listar y borrar suscripciones de Graph |
| `okf/` | Este bundle de contexto |

# Clientes soportados

Ver [índice de clientes](clients/index.md). Solo Danone, Penafiel, Holanda y Heineken están conectados de extremo a extremo. KOF tiene un stub.

# Dónde empezar

* Para entender un correo que llega: [recepción](flows/recepcion-correo.md) → [solicitud inicial](flows/solicitud-inicial.md).
* Para tocar datos: [capa de repositorio](data/capa-repositorio.md) y [modelo de datos](data/modelo-datos.md).
* Para saber qué está roto: [bugs](riesgos/bugs.md).

---
type: Configuration
title: config_general
description: Configuración compartida por todos los clientes. Mensajes HTML, palabras reservadas, stopwords y utilidades.
resource: https://github.com/pa70xd/e2c/blob/claude/admiring-lovelace-3oh7g0/config/config_general/
tags: [config, mensajes]
---

# Archivos

| Archivo | Contenido | Estado |
|---|---|---|
| `messages.py` (`MENSAJES_REPARE`) | 19 plantillas HTML de respuesta | Activo, con métodos sin uso |
| `palabras_reser.py` | Comandos reservados `bot.*` | Activo |
| `stopwords.py` | 60 palabras en español | Activo en gen y Danone utils |
| `fails_response.py` | 6 códigos de error | Parcialmente usado |
| `compact_names.py` | Nombre corto de Danone | Sin uso activo |
| `movimientos_list.py` | Tipos de movimiento | Sin uso |
| `distribuidoras.py` | Catálogo de distribuidoras | Ver [catálogos](../data/catalogos.md) |
| `querys/*.sql` | DDL de tablas de sábana y solicitud | Ver [capa de repositorio](../data/capa-repositorio.md) |

# Problemas

* `msj_fail` definido dos veces. La segunda sobrescribe a la primera.
* Métodos de mensaje sin llamadas: `msj_apertura`, `msj_respuesta`, `msj_reply_update_coolers`, `msj_reply_add_customer_cooler`, `msj_solicitud_completa`.
* Datos interpolados en HTML sin escapar.
* "Estimado usuario REPARE" literal en código compartido.
* `form_solicitud.sql` tiene una coma final antes de `);`. Invalida el DDL. Corregido en rama `claude/e2c-fix-mecanicos` (sin mergear).
* Tres versiones de `solicitudes_rechazadas` con esquemas distintos.

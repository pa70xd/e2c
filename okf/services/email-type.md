---
type: Module
title: email_type (clasificación)
description: Validación de correos, detección de cliente y dirección, y control de duplicados en memoria.
resource: https://github.com/pa70xd/e2c/blob/claude/admiring-lovelace-3oh7g0/src/email_type.py
tags: [clasificacion, validacion, duplicados]
---

# Responsabilidades

* `validate_email`: descarta borradores, correos automáticos (autorrespuesta, rebote, acuse), vacíos y duplicados.
* `detect_customer`: busca el buzón del cliente en To, CC y From con `config/email_index.json`.
* `detect_direccion`: inbound, outbound, reply_to_bot o bot. Mira To y From, no CC.
* Duplicados: ventana de 120 s en memoria por instancia. No se comparte entre instancias de Cloud Run.

# Constantes

* Remitente de Google ignorado.
* Prefijos de respuesta: `re:`, `rv:`, `fw:`, `fwd:`.
* Frase de plantilla del bot: "estimado usuario repare".

# Problemas

* `_is_auto_submitted` tiene un stub que se sobrescribe. Como `processMail` no pide `internetMessageHeaders`, esa rama y la de `in-reply-to` son código inerte.
* `detect_direccion` no mira CC, pero `detect_customer` sí. Inconsistente.
* `detect_direccion` puede devolver `None`. Ver [service](service.md).
* `"read:"` como patrón puede dar falsos positivos.
* No protege `email_address` ni `unique_body` nulos.

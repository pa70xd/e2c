---
type: Client Index
title: Clientes y buzones
description: Qué cliente llega por qué buzón, qué parser lo atiende y en qué estado está.
tags: [clientes, buzones]
---

# Mapeo de buzones

Fuente: `config/email_index.json`.

| Buzón | Cliente | Parser | Estado |
|---|---|---|---|
| `cliente.danone@repare.com.mx` | danone | [Danone](../parsers/danone.md) | Piloto, en producción |
| `cliente.holanda@repare.com.mx` | holanda | [Holanda](../parsers/holanda.md) | Activo |
| `cliente.kdrp@repare.com.mx` | penafiel | [Penafiel](../parsers/penafiel.md) | Activo |
| `cliente.hnk@repare.com.mx` | heineken | [Heineken](../parsers/heineken.md) | Mapeado, suscripción comentada en `subscriptions.py` |
| `<buzón de pruebas personal>` (dirección omitida; en la rama `claude/e2c-fix-holanda-indice` sale del índice y pasa a `E2C_TEST_MAILBOX`) | test | `test_*` | Buzón de prueba |

KOF: sin buzón mapeado, sin parser conectado. Ver [KOF](../parsers/kof.md).

# Cuenta distinta del cliente

Un correo puede venir de una cuenta que no es el cliente (por ejemplo, un cliente que llega por el buzón de Imbera). El código identifica al cliente por To, CC y From, no por el contenido del correo.

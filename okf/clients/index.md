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

**Fase 4, mergeado en la base (rama `claude/e2c-lector-excel`; verificado en `config/email_index.json`):** se agregan los buzones de rol `cliente.imbera`, `cliente.kof`, `cliente.torrey`, `cliente.oxxo` y `cliente.oxogar` (todos del dominio de REPARE), mapeados a los clientes `imbera`, `kof`, `torrey`, `oxxo` y `oxxo_garantias`. Detrás del flag `E2C_CLIENTES_HABILITADOS` (ver [despliegue](../deploy/despliegue.md)): sin definirla solo corren danone, holanda, penafiel (alias kdrp) y heineken (alias hnk). Cada cliente nuevo necesita su parser en `PARSERS_INIT`/`PARSERS_REPLY` de `src/service.py`; sin parser, el correo se ignora con log y no hay respuesta. `oxogar`/`oxxo_garantias` es el buzón de garantías de Oxxo ([Oxxo](../parsers/oxxo.md)); no se nombró en la lista aprobada el 2026-10-26. El flag lo mantiene apagado; falta confirmarlo con el usuario.

KOF: sin buzón mapeado, sin parser conectado. Ver [KOF](../parsers/kof.md).

# Cuenta distinta del cliente

Un correo puede venir de una cuenta que no es el cliente (por ejemplo, un cliente que llega por el buzón de Imbera). El código identifica al cliente por To, CC y From, no por el contenido del correo.

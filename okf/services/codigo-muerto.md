---
type: Known Issues
title: Código muerto del orquestador
description: Módulos y funciones que existen en el repo pero no se llaman desde el flujo.
tags: [codigo-muerto, deuda-tecnica]
---

# Sin importadores

* `src/attachments.py` (`DanoneAttachments`): nadie lo importa. Tiene `finally: pass` sin efecto y etiqueta de log `"debuger"`.
* `models/service_request.py` (`Template_Sabana`): solo aparece en un comentario de `service.py`.
* `config/config_general/movimientos_list.py`: sin importadores.
* `infrastructure/graphapi/graphapi.py`: `getTemplate`, `send_mail_file`, `sendMail`.
* `infrastructure/tableau/tableau.py`: `getModelo`.
* `infrastructure/database/engine_duck.py`: sin hallazgos, pero se usa poco.
* `parsers/kof.py`: stub, no registrado. Ver [KOF](../parsers/kof.md).

# Lista de decisiones

Antes de borrar cualquiera de estos, confirmar con el equipo. Algunos pueden ser piezas que se retomarán.

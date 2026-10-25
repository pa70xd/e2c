---
type: Risk Register
title: Seguridad
description: Riesgos de seguridad del repo, con prioridad sugerida.
tags: [seguridad, riesgos]
---

# Alta

1. **Webhook sin `clientState`**: `/receive_mail` no valida el origen. Cualquier POST con un id de mensaje real dispara el procesamiento. Verificado: no existe `clientState` en el repo.
   * **Estado**: mitigado en rama `claude/e2c-fix-orquestador`, sin mergear. Validación opcional con `GRAPH_CLIENT_STATE` (`hmac.compare_digest`). Pendiente: `subscriptions.py` no envía `clientState`, hay que agregarlo antes de activar la variable o se descartará todo. `/lifecyclenotif` sigue sin validar.
2. **Clave de cuenta de servicio en ruta Windows**: `excel_ingestion.py:25` referencia `C:\keys\...json`. Verificar si hay clave versionada o solo referencia.
3. **Datos personales versionados**: `email.json` y `email_model.json` con correos y nombres de terceros. Versionados (`git ls-files`). `.gitignore` lo marca pero no aplica.
4. **CORS abierto con credenciales**: `main.py:6-12` usa `allow_origins=["*"]` con `allow_credentials=True`.
   * **Estado**: corregido en rama `claude/e2c-fix-orquestador`, sin mergear. Con `CORS_ALLOW_ORIGINS` usa esos orígenes y credenciales; sin ella, `"*"` y `allow_credentials=False`.
5. **Dockerfile**: corre como root (no define `USER`). Sin `.dockerignore`: la imagen incluye `.git` y datos de prueba.

# Media

* `EMAIL_SENDER` hardcodeado, ignora `MAIL`.
* PII en logs de parsers y de DEBUG en `service.py:157-159`.
* Sin `sslmode` explícito en la conexión a PostgreSQL.
* Secreto de base de datos pedido en cada conexión a Secret Manager. Costo, no seguridad directa.
* Tableau: login en cada consulta.
* Requests sin timeout a Google Maps, Tableau y Graph.
* SQL armado con f-string en geocoding y excel_ingestion. No hay entrada de usuario sin escapar, pero es frágil.
* Comandos bot sin filtro por cliente en funciones genéricas. Riesgo bajo porque el código viene del hilo.
* Interpolación de HTML sin escape en plantillas de mensajes.

# Política

Antes de cualquier cambio, decidir si `email.json`, `email_model.json`, `mail.json` y los CSV con datos reales se eliminan del historial o solo del árbol.

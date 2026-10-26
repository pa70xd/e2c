"""Reglas de negocio de Torrey (buzón cliente.torrey@), wiki de Solkos.

  * Solo llegan garantías, consultas de estatus de OS y quejas o
    seguimientos. Toda solicitud con Excel es de garantía: se MARCA (la
    valida la etapa 2, no aquí).
  * Formato obligatorio: "Lay Out Repare" (mismo lector y layout que
    Imbera: config/customers/imbera/columns_names.py), con la factura en
    PDF. Sin factura PDF la solicitud se registra igual y la respuesta lo
    avisa (TODO: confirmar si debe rechazarse en la etapa 1).
  * Máquinas o fábricas de hielo: la OS se genera para el cliente IMBERA,
    pero se contesta en el hilo de Torrey (cooler_request.cliente = IMBERA;
    el email_request sigue siendo de Torrey). TODO: confirmar si deben ir
    en un email_request aparte con customer imbera.
"""

import re

CUSTOMER = "torrey"
CLIENTE_OS = "TORREY"

# Cliente de la OS para máquinas o fábricas de hielo.
CLIENTE_OS_HIELO = "IMBERA"

# Se busca en MODELO y FALLA (normalizados: mayúsculas, sin acentos).
# TODO: catálogo de modelos de máquinas de hielo de Torrey; hoy solo se
# reconoce por el texto ("máquina/fábrica de hielo", "ice maker").
PATRON_HIELO = re.compile(
    r"\b(MAQUINAS?|FABRICAS?|FABRICADORAS?|PRODUCTORAS?)\s+DE\s+HIELO\b|\bICE\s*MAKER\b"
)

# Toda solicitud de Torrey con Excel es de garantía.
SIEMPRE_GARANTIA = True

# Sin factura PDF: aviso en la respuesta (no rechaza).
EXIGE_FACTURA_PDF = True

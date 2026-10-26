"""Lo que cambia entre Imbera y Torrey. Todo lo demás (lector, reglas,
sábanas, persistencia, respuesta) es común y vive en parsers/imbera_parse/."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class PerfilLayout:
    # email_request.customer y emails_log.customer.
    customer: str
    # Prefijo de logs.
    etiqueta: str
    # cooler_request.cliente por defecto (cliente de la OS).
    cliente_os: str
    # Torrey: toda solicitud con Excel es de garantía.
    siempre_garantia: bool = False
    # Torrey: la respuesta avisa si falta la factura PDF.
    exige_factura_pdf: bool = False
    # Cliente de la OS por fila ({columna: valor} -> cliente o None para el
    # default). Torrey: máquinas de hielo -> IMBERA.
    cliente_os_fila: Callable[[dict], str | None] | None = None
    # Conciliación outbound desde el TEXTO ("orden generada: <n>"), además
    # de desde el Excel. Opcional por cliente.
    conciliar_texto: bool = True

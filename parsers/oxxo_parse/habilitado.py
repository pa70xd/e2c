"""Interruptor de los parsers de Oxxo.

Oxxo ya tiene una PoC automatizada fuera de este repo. Si las dos procesan
el mismo buzón se duplican las OS, así que los parsers de Oxxo están
APAGADOS por defecto: solo corren si su cliente ("oxxo" u "oxxo_garantias")
está en E2C_CLIENTES_HABILITADOS. La fuente de verdad del flag es
``src.email_type.cliente_habilitado`` (se lee en cada llamada); aquí solo se
usa, para que parser y servicio nunca discrepen."""

from src.email_type import cliente_habilitado, clientes_habilitados  # noqa: F401


def habilitado(cliente: str) -> bool:
    return cliente_habilitado(cliente.strip().lower())

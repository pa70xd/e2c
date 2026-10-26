"""Interruptor de los parsers de Oxxo.

Oxxo ya tiene una PoC automatizada fuera de este repo. Si las dos procesan
el mismo buzón se duplican las OS, así que los parsers de Oxxo están
APAGADOS por defecto: solo corren si su cliente ("oxxo" u "oxxo_garantias")
está en E2C_CLIENTES_HABILITADOS (lista separada por comas, sin distinguir
mayúsculas). La variable se lee en cada llamada, no al importar."""

import os

from config.customers.oxxo.reglas_oxxo import VAR_CLIENTES_HABILITADOS


def clientes_habilitados() -> frozenset[str]:
    crudo = os.getenv(VAR_CLIENTES_HABILITADOS, "")
    return frozenset(p.strip().lower() for p in crudo.split(",") if p.strip())


def habilitado(cliente: str) -> bool:
    return cliente.strip().lower() in clientes_habilitados()

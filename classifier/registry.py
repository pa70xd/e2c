"""Registro de proveedores y selección por variables de entorno.

* ``CLASSIFIER_GATE``: proveedor del gate (default ``regex``).
* ``CLASSIFIER_EXTRACT``: proveedor de la extracción (default ``regex``).
* ``CLASSIFIER_MIN_CONFIDENCE``: confianza mínima del gate externo (default 0.7).
* ``CLASSIFIER_SHADOW`` y ``CLASSIFIER_SHADOW_SAMPLE``: modo sombra, ver
  ``classifier/shadow.py``.

Son opcionales y nuevas. Se leen en cada llamada, así que no hace falta
reiniciar para cambiarlas en pruebas.

Candado de redacción (orquestadora, 2026-10-26): un proveedor externo
(gate, extract o sombra) solo corre si ``classifier.redact.REDACT_VERSION``
es al menos ``MIN_REDACT_VERSION`` (sin la constante cuenta como 1: la
redacción v1 deja escapar nombres y direcciones). Si no, se loguea un error
una sola vez, ``nombre_gate``/``nombre_extract`` devuelven ``regex`` y la
sombra no corre.
"""

from __future__ import annotations

import importlib
import os

from classifier.contracts import PROVEEDOR_REGEX, ProveedorNoDisponible

# nombre -> módulo. haiku y jev quedan registrados; los implementa otra sesión.
PROVEEDORES = {
    "regex": "classifier.providers.regex",
    "haiku": "classifier.providers.haiku",
    "jev": "classifier.providers.jev",
}

DEFAULT_MIN_CONFIDENCE = 0.7
MIN_REDACT_VERSION = 2

_candado_logueado = False


def redact_version() -> int:
    """``REDACT_VERSION`` de ``classifier/redact.py`` (1 si no la define, 0
    si el módulo no carga)."""
    try:
        from classifier import redact
    except Exception:
        return 0
    return getattr(redact, "REDACT_VERSION", 1)


def redaccion_apta(uso: str = "proveedor externo") -> bool:
    """True si la redacción permite mandar texto fuera. Si no, loguea un
    error una sola vez por proceso."""
    global _candado_logueado
    version = redact_version()
    if isinstance(version, int) and version >= MIN_REDACT_VERSION:
        return True
    if not _candado_logueado:
        _candado_logueado = True
        print(
            f"[CLASSIFIER][ERROR] REDACT_VERSION={version} < {MIN_REDACT_VERSION}: "
            f"{uso} desactivado (se usa regex y no corre la sombra)"
        )
    return False


def _configurado(var: str) -> str:
    return (os.getenv(var) or PROVEEDOR_REGEX).strip().lower() or PROVEEDOR_REGEX


def _nombre(var: str) -> str:
    nombre = _configurado(var)
    if nombre != PROVEEDOR_REGEX and not redaccion_apta(var):
        return PROVEEDOR_REGEX
    return nombre


def nombre_gate() -> str:
    return _nombre("CLASSIFIER_GATE")


def nombre_extract() -> str:
    return _nombre("CLASSIFIER_EXTRACT")


def verificar_redaccion() -> bool:
    """Chequeo al arrancar: si hay un proveedor externo o sombra configurado
    y la redacción no alcanza, deja el error en el log desde el inicio."""
    externos = [
        v for v in ("CLASSIFIER_GATE", "CLASSIFIER_EXTRACT")
        if _configurado(v) != PROVEEDOR_REGEX
    ]
    if (os.getenv("CLASSIFIER_SHADOW") or "").strip():
        externos.append("CLASSIFIER_SHADOW")
    if not externos:
        return True
    return redaccion_apta(",".join(externos))


def min_confidence() -> float:
    valor = os.getenv("CLASSIFIER_MIN_CONFIDENCE")
    if not valor:
        return DEFAULT_MIN_CONFIDENCE
    try:
        return float(valor)
    except ValueError:
        return DEFAULT_MIN_CONFIDENCE


def cargar(nombre: str):
    """Módulo del proveedor. ``ProveedorNoDisponible`` si no existe."""
    modulo = PROVEEDORES.get(nombre)
    if modulo is None:
        raise ProveedorNoDisponible(f"proveedor_desconocido:{nombre}")
    try:
        return importlib.import_module(modulo)
    except ModuleNotFoundError as e:
        if e.name != modulo:
            raise
        raise ProveedorNoDisponible(f"proveedor_no_implementado:{nombre}") from None


def get_redactor():
    """``redact(text, conservar=())`` de ``classifier/redact.py``."""
    from classifier.redact import redact
    return redact

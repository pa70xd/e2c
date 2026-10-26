"""Registro de proveedores y selección por variables de entorno.

* ``CLASSIFIER_GATE``: proveedor del gate (default ``regex``).
* ``CLASSIFIER_EXTRACT``: proveedor de la extracción (default ``regex``).
* ``CLASSIFIER_MIN_CONFIDENCE``: confianza mínima del gate externo (default 0.7).
* ``CLASSIFIER_SHADOW`` y ``CLASSIFIER_SHADOW_SAMPLE``: modo sombra, ver
  ``classifier/shadow.py``.

Son opcionales y nuevas. Se leen en cada llamada, así que no hace falta
reiniciar para cambiarlas en pruebas.
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


def _nombre(var: str) -> str:
    return (os.getenv(var) or PROVEEDOR_REGEX).strip().lower() or PROVEEDOR_REGEX


def nombre_gate() -> str:
    return _nombre("CLASSIFIER_GATE")


def nombre_extract() -> str:
    return _nombre("CLASSIFIER_EXTRACT")


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

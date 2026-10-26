"""Utilidades de las pruebas del clasificador.

Cada prueba arranca con los proveedores por defecto (``regex``) y sin
cargador de contexto, aunque el entorno tenga ``CLASSIFIER_*``.
"""

import sys
import types

import pytest

import classifier
from classifier import registry


@pytest.fixture(autouse=True)
def _clasificador_por_defecto(monkeypatch):
    for var in ("CLASSIFIER_GATE", "CLASSIFIER_EXTRACT", "CLASSIFIER_MIN_CONFIDENCE", "CLASSIFIER_PROMPT_VERSION",
                "CLASSIFIER_SHADOW", "CLASSIFIER_SHADOW_SAMPLE"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(classifier, "_cargador_contexto", None)


class Proveedores:
    """Registra proveedores falsos (módulos en memoria) y un redactor falso."""

    def __init__(self, monkeypatch):
        self.mp = monkeypatch
        self.redactados = []

    def registrar(self, nombre, gate=None, extract=None):
        modulo = types.ModuleType(f"tests_fake_provider_{nombre}")
        modulo.NAME = nombre
        if gate is not None:
            modulo.gate = gate
        if extract is not None:
            modulo.extract = extract
        self.mp.setitem(sys.modules, modulo.__name__, modulo)
        self.mp.setitem(registry.PROVEEDORES, nombre, modulo.__name__)
        return modulo

    def redactor(self, fn=None):
        def redact(text, conservar=()):
            self.redactados.append((text, tuple(conservar)))
            return "<R>" if fn is None else fn(text)
        self.mp.setattr(registry, "get_redactor", lambda: redact)

    def sin_redaccion(self, error=NotImplementedError):
        def redact(text, conservar=()):
            raise error("redacción caída")
        self.mp.setattr(registry, "get_redactor", lambda: redact)

    def usar(self, gate=None, extract=None):
        if gate:
            self.mp.setenv("CLASSIFIER_GATE", gate)
        if extract:
            self.mp.setenv("CLASSIFIER_EXTRACT", extract)


@pytest.fixture
def proveedores(monkeypatch):
    return Proveedores(monkeypatch)

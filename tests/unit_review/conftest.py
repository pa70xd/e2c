"""El candado de redacción (``REDACT_VERSION`` >= 2) se da por cumplido: estas
pruebas usan proveedores falsos y redactores de prueba."""

import pytest

from classifier import registry


@pytest.fixture(autouse=True)
def _redaccion_apta(monkeypatch):
    monkeypatch.setattr(registry, "redact_version", lambda: registry.MIN_REDACT_VERSION)
    monkeypatch.setattr(registry, "_candado_logueado", False)

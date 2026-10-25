"""El evaluador fija CLASSIFIER_* en os.environ; cada prueba arranca limpia."""

import pytest

import classifier


@pytest.fixture(autouse=True)
def _clasificador_por_defecto(monkeypatch):
    for var in ("CLASSIFIER_GATE", "CLASSIFIER_EXTRACT", "CLASSIFIER_MIN_CONFIDENCE"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(classifier, "_cargador_contexto", None)

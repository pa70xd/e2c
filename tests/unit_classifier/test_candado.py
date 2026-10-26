"""Candado de redacción: sin REDACT_VERSION >= 2 no sale texto a un proveedor
externo ni a la sombra (cae a regex), con un solo error en el log."""

from types import SimpleNamespace

import pytest

import classifier
from classifier import registry, shadow
from classifier.contracts import ETAPA_REPLY, GateResult, ThreadCtx

CTX = ThreadCtx(etapa=ETAPA_REPLY, customer="danone", direccion="inbound")


# La función real, capturada al importar (antes del parche del conftest).
REDACT_VERSION_REAL = registry.redact_version


@pytest.fixture
def externo(proveedores):
    llamadas = []
    proveedores.registrar("fake", gate=lambda s, b, c: llamadas.append(1) or GateResult(True, "cancelar_filas", 0.95),
                          extract=lambda b, c, gate=None: llamadas.append(2) or [])
    proveedores.redactor()
    return llamadas


def test_redact_version_lee_la_constante(monkeypatch):
    from classifier import redact
    monkeypatch.setattr(registry, "redact_version", REDACT_VERSION_REAL)
    monkeypatch.delattr(redact, "REDACT_VERSION", raising=False)
    assert registry.redact_version() == 1  # sin constante = v1
    monkeypatch.setattr(redact, "REDACT_VERSION", 2, raising=False)
    assert registry.redact_version() == 2
    assert registry.redaccion_apta()


def test_v1_desactiva_gate_y_extract_externos(monkeypatch, proveedores, externo, capsys):
    monkeypatch.setattr(registry, "redact_version", lambda: 1)
    proveedores.usar(gate="fake", extract="fake")
    assert registry.nombre_gate() == registry.nombre_extract() == "regex"
    d = classifier.decidir("RE: x", "cuerpo", CTX)
    assert d.proveedor_gate == d.proveedor_extract == "regex"
    assert externo == [] and proveedores.redactados == []
    assert capsys.readouterr().out.count("[CLASSIFIER][ERROR] REDACT_VERSION=1 < 2") == 1


def test_error_se_loguea_una_sola_vez(monkeypatch, proveedores, capsys):
    monkeypatch.setattr(registry, "redact_version", lambda: 1)
    proveedores.usar(gate="fake")
    for _ in range(5):
        registry.nombre_gate()
        registry.verificar_redaccion()
    assert capsys.readouterr().out.count("REDACT_VERSION") == 1


def test_v2_deja_correr_el_externo(proveedores, externo):
    proveedores.usar(gate="fake", extract="fake")
    d = classifier.decidir("RE: x", "cuerpo", CTX)
    assert d.proveedor_gate == "fake" and externo


def test_v1_no_corre_la_sombra(monkeypatch, proveedores, externo, capsys):
    monkeypatch.setattr(registry, "redact_version", lambda: 1)
    monkeypatch.setenv("CLASSIFIER_SHADOW", "fake")
    email = SimpleNamespace(id="x", subject="s", unique_body=SimpleNamespace(content="b"))
    assert shadow.lanzar(email, classifier.decidir("s", "b", CTX), CTX) is None
    assert externo == []
    out = capsys.readouterr().out
    assert "[CLASSIFIER][ERROR] REDACT_VERSION=1" in out and "CLASSIFIER_SHADOW" in out
    assert "[CLASSIFIER_SHADOW] " not in out


def test_v1_gate_externo_cae_y_la_sombra_regex_no_duplica(monkeypatch, proveedores, externo):
    # El candado deja el gate activo en regex; una sombra regex sería igual.
    monkeypatch.setattr(registry, "redact_version", lambda: 1)
    monkeypatch.setenv("CLASSIFIER_SHADOW", "regex")
    proveedores.usar(gate="fake")
    email = SimpleNamespace(id="x", subject="s", unique_body=SimpleNamespace(content="b"))
    assert shadow.lanzar(email, classifier.decidir("s", "b", CTX), CTX) is None
    assert externo == []


@pytest.mark.parametrize("env, apta", [
    ({}, True),
    ({"CLASSIFIER_GATE": "regex"}, True),
    ({"CLASSIFIER_GATE": "haiku"}, False),
    ({"CLASSIFIER_EXTRACT": "haiku"}, False),
    ({"CLASSIFIER_SHADOW": "haiku"}, False),
], ids=["default", "regex", "gate", "extract", "sombra"])
def test_verificar_redaccion_al_arrancar(monkeypatch, capsys, env, apta):
    monkeypatch.setattr(registry, "redact_version", lambda: 1)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    assert registry.verificar_redaccion() is apta
    assert ("REDACT_VERSION" in capsys.readouterr().out) is (not apta)


def test_redact_que_no_carga_cuenta_como_0(monkeypatch):
    import sys
    monkeypatch.setattr(registry, "redact_version", REDACT_VERSION_REAL)
    monkeypatch.setitem(sys.modules, "classifier.redact", None)  # import falla
    monkeypatch.delattr(classifier, "redact", raising=False)
    assert registry.redact_version() == 0

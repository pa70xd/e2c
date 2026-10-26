"""Modo sombra: corre otro proveedor, solo registra y nunca afecta el flujo."""

import json
import threading
from types import SimpleNamespace

import pytest

import classifier
from classifier import registry, shadow
from classifier.contracts import (
    ACCEPTED,
    ETAPA_INIT,
    ETAPA_REPLY,
    FilaGuardada,
    GateResult,
    ProveedorNoDisponible,
    ThreadCtx,
)

CUERPO = "Cambien la serie SF-PRIVADA-77 de Calle Inventada 42, contacto juan.perez@cliente.mx"
ASUNTO = "RE: Solicitud folio FOL-9988 de Juan Pérez"
MID = "<AAMk-secreto-123@mail.example.com>"


def _email():
    return SimpleNamespace(
        id="graph-id-1",
        internet_message_id=MID,
        subject=ASUNTO,
        unique_body=SimpleNamespace(content=CUERPO),
        has_attachments=False,
    )


CTX = ThreadCtx(etapa=ETAPA_REPLY, customer="danone", direccion="inbound")


def _real(ctx=CTX):
    return classifier.decidir(ASUNTO, CUERPO, ctx)


def _registros(capsys):
    lineas = [l for l in capsys.readouterr().out.splitlines() if l.startswith(shadow.PREFIJO + " ")]
    return [json.loads(l[len(shadow.PREFIJO) + 1:]) for l in lineas]


def _correr(email=None, decision=None, ctx=CTX):
    hilo = shadow.lanzar(email or _email(), decision or _real(ctx), ctx)
    assert hilo is not None and hilo.daemon
    hilo.join(5)
    return hilo


@pytest.fixture
def sombra(proveedores, monkeypatch):
    def activar(gate, nombre="fake", **kw):
        modulo = proveedores.registrar(nombre, gate=gate)
        for k, v in kw.items():
            setattr(modulo, k, v)
        monkeypatch.setenv("CLASSIFIER_SHADOW", nombre)
        return modulo
    proveedores.redactor(lambda t: "<R>")
    return activar


def test_sin_variable_no_corre(capsys):
    assert shadow.nombre_sombra() is None
    assert shadow.lanzar(_email(), _real(), CTX) is None
    assert capsys.readouterr().out == ""


def test_misma_que_el_gate_activo_no_corre(sombra, monkeypatch, proveedores):
    sombra(lambda s, b, c: GateResult(True, "estatus", 0.9))
    proveedores.usar(gate="fake")
    assert shadow.lanzar(_email(), _real(), CTX) is None


def test_registra_una_linea_json_sin_pii(sombra, capsys):
    vistos = []

    def gate(s, b, c):
        vistos.append((s, b))
        return GateResult(False, "no_os", 0.91)

    sombra(gate, version_prompt=lambda op: "gate-v9")
    d = _real()
    capsys.readouterr()
    _correr(decision=d)

    (r,) = _registros(capsys)
    assert vistos == [("<R>", "<R>")]  # redactado antes del proveedor externo
    assert r["message_id_hash"] == shadow.hash_id(MID) and len(r["message_id_hash"]) == 16
    assert r["customer"] == "danone" and r["etapa"] == "reply" and r["direccion"] == "inbound"
    assert r["real"] == {"proveedor": "regex", "es_os": True, "tipo_evento": "modificar_filas", "confidence": 1.0}
    assert r["sombra"] == {"proveedor": "fake", "es_os": False, "tipo_evento": "no_os",
                           "confidence": 0.91, "motivo_caida": None}
    assert r["coinciden"] is False
    assert isinstance(r["latencia_ms"], int)
    assert r["prompt_version"] == "gate-v9"


def test_nunca_sale_texto_del_correo(sombra, capsys):
    sombra(lambda s, b, c: GateResult(True, "modificar_filas", 0.95, detalle="SF-PRIVADA-77"))
    _correr()
    out = capsys.readouterr().out
    for prohibido in ("SF-PRIVADA-77", "Calle Inventada", "juan.perez", "FOL-9988", "Juan", MID, "AAMk", "graph-id-1"):
        assert prohibido not in out


def test_coinciden(sombra, capsys):
    sombra(lambda s, b, c: GateResult(True, "modificar_filas", 0.8))
    _correr()
    (r,) = _registros(capsys)
    assert r["coinciden"] is True


@pytest.mark.parametrize("gate, motivo, con_salida", [
    (lambda s, b, c: GateResult(True, "estatus", 0.2), "gate:confianza_baja", True),
    (lambda s, b, c: GateResult(True, "nueva_solicitud", 0.9), "ctx:nueva_solicitud_en_hilo", True),
    (lambda s, b, c: {"es_os": True}, "gate:tipo_invalido", False),
], ids=["confianza_baja", "ctx", "invalida"])
def test_motivo_de_caida_por_validacion(sombra, capsys, gate, motivo, con_salida):
    sombra(gate)
    _correr()
    (r,) = _registros(capsys)
    assert r["sombra"]["motivo_caida"] == motivo
    assert (r["coinciden"] is not None) is con_salida


@pytest.mark.parametrize("error, motivo", [
    (RuntimeError("texto secreto del correo"), "RuntimeError"),
    (ProveedorNoDisponible("haiku_sin_api_key"), "haiku_sin_api_key"),
])
def test_excepcion_del_proveedor_no_se_propaga(sombra, capsys, error, motivo):
    def gate(*a):
        raise error
    sombra(gate)
    _correr()
    out = capsys.readouterr().out
    assert "secreto" not in out
    (r,) = [json.loads(l.split(" ", 1)[1]) for l in out.splitlines() if l.startswith(shadow.PREFIJO + " ")]
    assert r["sombra"]["motivo_caida"] == motivo and r["coinciden"] is None


def test_redaccion_caida_no_llama_al_proveedor(proveedores, monkeypatch, capsys):
    llamadas = []
    proveedores.registrar("fake", gate=lambda *a: llamadas.append(1))
    proveedores.sin_redaccion()
    monkeypatch.setenv("CLASSIFIER_SHADOW", "fake")
    _correr()
    (r,) = _registros(capsys)
    assert llamadas == [] and r["sombra"]["motivo_caida"] == "redaccion_error"


def test_proveedor_desconocido(monkeypatch, capsys):
    monkeypatch.setenv("CLASSIFIER_SHADOW", "nada")
    _correr()
    (r,) = _registros(capsys)
    assert r["sombra"]["motivo_caida"] == "proveedor_desconocido:nada"


def test_timeout_no_bloquea(sombra, monkeypatch, capsys):
    liberar = threading.Event()
    sombra(lambda *a: liberar.wait(5) and GateResult(True, "estatus", 0.9))
    monkeypatch.setattr(shadow, "TIMEOUT_S", 0.05)
    _correr()
    liberar.set()
    (r,) = _registros(capsys)
    assert r["sombra"]["motivo_caida"] == "shadow_timeout"


def test_lanzar_no_espera_a_la_sombra(sombra):
    liberar = threading.Event()
    sombra(lambda *a: liberar.wait(5) and GateResult(True, "estatus", 0.9))
    import time
    t0 = time.monotonic()
    hilo = shadow.lanzar(_email(), _real(), CTX)
    assert time.monotonic() - t0 < 0.5
    liberar.set()
    hilo.join(5)


@pytest.mark.parametrize("valor, esperado", [
    (None, 1.0), ("", 1.0), ("0.25", 0.25), ("2", 1.0), ("-1", 0.0), ("x", 1.0),
])
def test_muestra(monkeypatch, valor, esperado):
    if valor is None:
        monkeypatch.delenv("CLASSIFIER_SHADOW_SAMPLE", raising=False)
    else:
        monkeypatch.setenv("CLASSIFIER_SHADOW_SAMPLE", valor)
    assert shadow.muestra() == esperado


def test_muestra_cero_no_corre(sombra, monkeypatch):
    sombra(lambda s, b, c: GateResult(True, "estatus", 0.9))
    monkeypatch.setenv("CLASSIFIER_SHADOW_SAMPLE", "0")
    assert shadow.lanzar(_email(), _real(), CTX) is None


def test_muestra_usa_random(sombra, monkeypatch):
    sombra(lambda s, b, c: GateResult(True, "estatus", 0.9))
    monkeypatch.setenv("CLASSIFIER_SHADOW_SAMPLE", "0.5")
    monkeypatch.setattr(shadow.random, "random", lambda: 0.7)
    assert shadow.lanzar(_email(), _real(), CTX) is None
    monkeypatch.setattr(shadow.random, "random", lambda: 0.3)
    shadow.lanzar(_email(), _real(), CTX).join(5)


def test_carga_el_contexto_del_hilo_para_la_sombra(sombra, monkeypatch, capsys):
    vistos = []
    sombra(lambda s, b, c: vistos.append(c) or GateResult(True, "estatus", 0.9))
    filas = (FilaGuardada(1, ACCEPTED, "SF-PRIVADA-77"),)
    monkeypatch.setattr(classifier, "_cargador_contexto",
                        lambda email, ctx: ThreadCtx(**{**ctx.__dict__, "request_code": "RC", "filas": filas}))
    _correr()
    assert vistos[0].filas == filas
    assert "SF-PRIVADA-77" not in capsys.readouterr().out


def test_init_sin_cargador(sombra, monkeypatch, capsys):
    llamadas = []
    sombra(lambda s, b, c: GateResult(True, "nueva_solicitud", 0.9))
    monkeypatch.setattr(classifier, "_cargador_contexto", lambda e, c: llamadas.append(1) or c)
    ctx = ThreadCtx(etapa=ETAPA_INIT, customer="holanda")
    _correr(ctx=ctx)
    assert llamadas == []
    (r,) = _registros(capsys)
    assert r["etapa"] == "init" and r["coinciden"] is True


def test_sin_message_id(sombra, capsys):
    sombra(lambda s, b, c: GateResult(True, "estatus", 0.9))
    _correr(email=SimpleNamespace(subject=None, unique_body=None))
    (r,) = _registros(capsys)
    assert r["message_id_hash"] is None


def test_lanzar_nunca_lanza(monkeypatch, capsys):
    monkeypatch.setenv("CLASSIFIER_SHADOW", "fake")
    d = _real()
    monkeypatch.setattr(registry, "nombre_gate", lambda: (_ for _ in ()).throw(ValueError("x")))
    assert shadow.lanzar(_email(), d, CTX) is None
    assert "[CLASSIFIER_SHADOW][ERROR] ValueError" in capsys.readouterr().out


def test_sin_decision_no_corre(monkeypatch):
    monkeypatch.setenv("CLASSIFIER_SHADOW", "haiku")
    assert shadow.lanzar(_email(), None, CTX) is None
    assert shadow.lanzar(_email(), _real(), None) is None


def test_sombra_regex_con_gate_externo_activo(proveedores, monkeypatch, capsys):
    proveedores.registrar("fake", gate=lambda s, b, c: GateResult(True, "cancelar_filas", 0.95))
    proveedores.redactor()
    proveedores.usar(gate="fake")
    monkeypatch.setenv("CLASSIFIER_SHADOW", "regex")
    d = _real()
    capsys.readouterr()
    _correr(decision=d)
    (r,) = _registros(capsys)
    assert r["real"]["proveedor"] == "fake" and r["sombra"]["proveedor"] == "regex"
    assert r["sombra"]["tipo_evento"] == "modificar_filas" and r["coinciden"] is False
    assert r["prompt_version"] is None


# ------------------------------------------------------------ processMail
def _esperar_sombras():
    for t in threading.enumerate():
        if t.name.startswith("classifier-shadow"):
            t.join(5)


def test_process_mail_con_sombra_no_cambia_el_flujo(harness, sombra, capsys):
    from tests.support.emails import CLIENTES, REPARE, make_email

    def correo(n):
        return make_email(
            subject="RE: Solicitud de servicio", body="Cancelen la fila 1.",
            sender=CLIENTES["danone"], to=[REPARE["danone"]],
            conversation_id=f"conv-sombra-{n}", message_id=f"msg-sombra-{n}", has_attachments=False,
        )

    harness.repo.set("conversation_exists", True)
    harness.deliver(correo("a"))
    ref_replies, ref_calls = list(harness.replies), harness.repo.names()

    sombra(lambda s, b, c: GateResult(False, "no_os", 0.99))
    harness.deliver(correo("b"))
    _esperar_sombras()

    assert harness.replies[len(ref_replies):] == [] and ref_replies == []
    assert harness.repo.names()[len(ref_calls):] == ref_calls
    (r,) = _registros(capsys)
    assert r["message_id_hash"] == shadow.hash_id("<msg-sombra-b@mail.example.com>")
    assert r["real"]["es_os"] is True and r["sombra"]["es_os"] is False

"""Proveedor haiku con el cliente de Anthropic mockeado (sin red)."""

import json
from types import SimpleNamespace

import anthropic
import httpx2
import pytest

from classifier import decidir, registry, validate
from classifier.contracts import (
    DecisionPrevia,
    FilaGuardada,
    GateResult,
    ProveedorNoDisponible,
    RowExtraida,
    ThreadCtx,
)
from classifier.providers import haiku

REQ = httpx2.Request("POST", "https://api.anthropic.test/v1/messages")

CTX_INIT = ThreadCtx(etapa="init", customer="danone")
CTX_REPLY = ThreadCtx(
    etapa="reply",
    customer="danone",
    direccion="inbound",
    decisiones=(DecisionPrevia("nueva_solicitud", True, "haiku"),),
    filas=(
        FilaGuardada(1, "PENDING", "SF-1001"),
        FilaGuardada(2, "ACCEPTED", "SF-2002", "DNN-2"),
    ),
)


def _resp(payload, stop_reason="end_turn", texto=None):
    texto = json.dumps(payload) if texto is None else texto
    return SimpleNamespace(
        stop_reason=stop_reason,
        content=[SimpleNamespace(type="text", text=texto)],
        usage=SimpleNamespace(cache_read_input_tokens=0, cache_creation_input_tokens=0),
    )


class FakeClient:
    def __init__(self, respuesta=None, error=None):
        self.llamadas = []
        self._respuesta = respuesta
        self._error = error
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.llamadas.append(kwargs)
        if self._error:
            raise self._error
        return self._respuesta


@pytest.fixture
def cliente(monkeypatch):
    """Instala un FakeClient; ``cliente(resp)`` o ``cliente(error=...)``."""
    def instalar(respuesta=None, error=None):
        fake = FakeClient(respuesta, error)
        monkeypatch.setattr(haiku, "_get_client", lambda: fake)
        return fake
    return instalar


GATE_OK = {"es_os": True, "tipo_evento": "modificar_filas", "confidence": 0.9, "detalle": "corrige modelo"}


def _fila(**kw):
    base = dict(accion="modificar", folio=None, serie_fabricante=None, serie_dnn_bnf=None,
                modelo=None, tipo_servicio=None, direccion=None, row_number=1)
    base.update(kw)
    return base


# ------------------------------------------------------------------ válidas
def test_gate_valido(cliente):
    fake = cliente(_resp(GATE_OK))
    r = haiku.gate("Cambio", "En la segunda fila el modelo está mal", CTX_REPLY)
    assert r == GateResult(True, "modificar_filas", 0.9, "corrige modelo")
    assert validate.validar_gate(r, CTX_REPLY, 0.7) == []

    llamada = fake.llamadas[0]
    assert llamada["model"] == "claude-haiku-5-5"
    assert "temperature" not in llamada
    # parte fija cacheada; el hilo y el correo van en el mensaje
    assert llamada["system"][0]["cache_control"] == {"type": "ephemeral"}
    msg = llamada["messages"][0]["content"]
    assert "fila 2 (ACCEPTED): SF-2002, DNN-2" in msg
    assert "nueva_solicitud(es_os=True)" in msg
    assert "En la segunda fila" in msg
    assert "SF-2002" not in llamada["system"][0]["text"]
    enum = llamada["output_config"]["format"]["schema"]["properties"]["tipo_evento"]["enum"]
    assert "cancelar_solicitud" in enum and len(enum) == 8


def test_extract_valido(cliente):
    cliente(_resp({"rows": [_fila(tipo_servicio="correctivo", row_number=1)]}))
    rows = haiku.extract("En la primera fila el servicio es correctivo", CTX_REPLY)
    assert rows == [RowExtraida("modificar", tipo_servicio="correctivo", row_number=1)]
    gate = GateResult(True, "modificar_filas", 0.9)
    assert validate.validar_rows(rows, gate, CTX_REPLY) == []


def test_extract_vacio(cliente):
    cliente(_resp({"rows": []}))
    assert haiku.extract("Gracias", CTX_REPLY) == []


def test_extract_init_sin_filas_cargadas(cliente):
    cliente(_resp({"rows": [_fila(accion="agregar", serie_fabricante="SF-1", row_number=None)]}))
    rows = haiku.extract("Solicito servicio, serie SF-1", CTX_INIT)
    assert rows[0].accion == "agregar"


def test_prompts_versionados_con_ejemplos():
    for nombre in ("gate", "extract"):
        texto, version = haiku._prompt(nombre)
        assert version == f"{nombre}-v1"
        assert 6 <= texto.count("\nEjemplo ") <= 10
    assert haiku._hay_pii(haiku._prompt("gate")[0], haiku._prompt("extract")[0]) is False


# ------------------------------------------------------------------ salida inválida
@pytest.mark.parametrize("texto", ["no es json", "", "[1, 2]"])
def test_json_invalido(cliente, texto):
    cliente(_resp(None, texto=texto))
    with pytest.raises(haiku.HaikuSalidaInvalida):
        haiku.gate("a", "b", CTX_REPLY)


def test_campos_faltantes(cliente):
    cliente(_resp({"es_os": True}))
    with pytest.raises(haiku.HaikuSalidaInvalida):
        haiku.gate("a", "b", CTX_REPLY)
    cliente(_resp({"otra": []}))
    with pytest.raises(haiku.HaikuSalidaInvalida):
        haiku.extract("b", CTX_REPLY)


def test_max_tokens_y_rechazo(cliente):
    cliente(_resp(GATE_OK, stop_reason="max_tokens"))
    with pytest.raises(haiku.HaikuSalidaInvalida):
        haiku.gate("a", "b", CTX_REPLY)
    cliente(_resp(GATE_OK, stop_reason="refusal"))
    with pytest.raises(haiku.HaikuRechazo):
        haiku.gate("a", "b", CTX_REPLY)


def test_enum_fuera_de_rango_lo_rechaza_validate(cliente):
    cliente(_resp({**GATE_OK, "tipo_evento": "inventado"}))
    r = haiku.gate("a", "b", CTX_REPLY)
    assert "gate:tipo_evento_invalido" in validate.validar_gate(r, CTX_REPLY, 0.7)

    cliente(_resp({"rows": [_fila(accion="borrar")]}))
    rows = haiku.extract("b", CTX_REPLY)
    gate = GateResult(True, "modificar_filas", 0.9)
    assert "rows[0]:accion_invalida" in validate.validar_rows(rows, gate, CTX_REPLY)

    cliente(_resp({"rows": [_fila(row_number=99)]}))
    rows = haiku.extract("b", CTX_REPLY)
    assert "rows[0]:fila_inexistente" in validate.validar_rows(rows, gate, CTX_REPLY)


# ------------------------------------------------------------------ fallas
def test_timeout(cliente):
    cliente(error=anthropic.APITimeoutError(request=REQ))
    with pytest.raises(haiku.HaikuTimeout):
        haiku.gate("a", "b", CTX_REPLY)


def test_error_de_api(cliente):
    resp = httpx2.Response(500, request=REQ)
    cliente(error=anthropic.InternalServerError("secreto del correo", response=resp, body=None))
    with pytest.raises(haiku.HaikuApiError) as e:
        haiku.extract("b", CTX_REPLY)
    assert "secreto" not in str(e.value)


def test_cliente_con_timeout_corto_y_pocos_reintentos(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "clave-de-prueba")
    monkeypatch.setattr(haiku, "_client", None)
    c = haiku._get_client()
    assert c.max_retries == haiku.MAX_RETRIES <= 1
    assert haiku.TIMEOUT_S <= 10


# ------------------------------------------------------------------ API key
def test_sin_api_key(monkeypatch, capsys):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ProveedorNoDisponible, match="haiku_sin_api_key"):
        haiku.gate("a", "b", CTX_REPLY)
    assert "ANTHROPIC_API_KEY no configurada" in capsys.readouterr().out


def test_sin_api_key_cae_a_regex(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("CLASSIFIER_GATE", "haiku")
    monkeypatch.setenv("CLASSIFIER_EXTRACT", "haiku")
    monkeypatch.setattr(registry, "get_redactor", lambda: (lambda t: t))  # redact.py es de otra sesión
    d = decidir("Asunto", "bot.estatus", CTX_REPLY)
    assert d.proveedor_gate == "regex" and d.proveedor_extract == "regex"
    assert "gate:haiku:haiku_sin_api_key" in d.fallbacks


# ------------------------------------------------------------------ PII
@pytest.mark.parametrize("texto", [
    "escribe a persona@ejemplo.com",
    "llámame al 55 1234 5678",
    "tel: 5512345678",
    "+52 55 1234 5678",
    "(55) 1234-5678",
])
def test_pii_sin_redactar_no_llama(cliente, texto):
    fake = cliente(_resp(GATE_OK))
    with pytest.raises(ProveedorNoDisponible, match="haiku_pii_sin_redactar"):
        haiku.gate("asunto", texto, CTX_REPLY)
    with pytest.raises(ProveedorNoDisponible, match="haiku_pii_sin_redactar"):
        haiku.extract(texto, CTX_REPLY)
    with pytest.raises(ProveedorNoDisponible):
        haiku.gate(texto, "cuerpo limpio", CTX_REPLY)
    assert fake.llamadas == []


def test_series_no_son_telefonos(cliente):
    cliente(_resp(GATE_OK))
    haiku.gate("a", "serie 1234567890 y SF-1001 modelo VR-26", CTX_REPLY)


def test_pii_cae_a_regex_via_decidir(cliente, monkeypatch):
    fake = cliente(_resp(GATE_OK))
    monkeypatch.setenv("CLASSIFIER_GATE", "haiku")
    monkeypatch.setattr(registry, "get_redactor", lambda: (lambda t: t))  # redactor que no quita nada
    d = decidir("Asunto", "bot.estatus de persona@ejemplo.com", CTX_REPLY)
    assert d.proveedor_gate == "regex"
    assert d.fallbacks == ("gate:haiku:haiku_pii_sin_redactar",)
    assert fake.llamadas == []


def test_extract_reply_sin_filas_cargadas(cliente):
    fake = cliente(_resp({"rows": []}))
    ctx = ThreadCtx(etapa="reply", filas=None)
    with pytest.raises(ProveedorNoDisponible):
        haiku.extract("cancelen la primera", ctx)
    assert fake.llamadas == []


# ------------------------------------------------------------------ logs
def test_logs_sin_pii(cliente, capsys):
    cliente(_resp(GATE_OK))
    haiku.gate("Asunto secreto", "Texto del correo con SF-9999", CTX_REPLY)
    out = capsys.readouterr().out
    assert "tipo_evento=modificar_filas" in out and "confidence=0.9" in out and "latencia_ms=" in out
    assert "secreto" not in out and "SF-9999" not in out and "Texto del correo" not in out

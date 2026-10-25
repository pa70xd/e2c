"""El proveedor regex reproduce exactamente la lógica anterior."""

import pytest

import classifier
from classifier.contracts import (
    CANCELAR_SOLICITUD,
    ESTATUS,
    ETAPA_INIT,
    ETAPA_REPLY,
    MODIFICAR_FILAS,
    NO_OS,
    NUEVA_SOLICITUD,
    ThreadCtx,
)
from classifier.providers import regex
from parsers.danone_parse.utils import DANONE_UTILS
from parsers.penafiel_parse.utils import PENAFIEL_UTILS

TEXTOS = [
    ("favor de realizar instalaciones", "Solicitud"),
    ("<p>Me apoyan con <b>RETIRO</b> de equipos</p>", "RE: pedido"),
    ("solicito reubicacion", ""),
    ("gracias, saludos", "Hola"),
    ("Se realizó la instalación", "Hola"),
    ("orden de servicio adjunta", "OS"),
    ("", "Instalaciones"),
    ("muchas gracias por el apoyo", "Confirmacion"),
]


@pytest.mark.parametrize("cuerpo, asunto", TEXTOS)
def test_danone_gate_igual_a_analizar_proposito(cuerpo, asunto):
    esperado = DANONE_UTILS.analizar_proposito_regex(cuerpo, asunto)
    assert DANONE_UTILS.analizar_proposito(cuerpo, asunto) is esperado
    r = regex.gate(asunto, cuerpo, ThreadCtx(etapa=ETAPA_INIT, customer="danone"))
    assert r.es_os is esperado
    assert r.tipo_evento == (NUEVA_SOLICITUD if esperado else NO_OS)
    assert r.confidence == 1.0


@pytest.mark.parametrize("cuerpo, asunto", TEXTOS)
def test_penafiel_gate_igual_a_analizar_proposito(cuerpo, asunto):
    texto = cuerpo + asunto  # como parsers/penafiel.py
    esperado = PENAFIEL_UTILS.analizar_proposito_regex(texto)
    assert PENAFIEL_UTILS.analizar_proposito(texto) is esperado
    r = regex.gate(None, texto, ThreadCtx(etapa=ETAPA_INIT, customer="test_penafiel"))
    assert r.es_os is esperado
    # Con asunto separado concatena igual que el parser.
    r2 = regex.gate(asunto, cuerpo, ThreadCtx(etapa=ETAPA_INIT, customer="penafiel"))
    assert r2.es_os is esperado


def test_penafiel_texto_nulo_sigue_siendo_false():
    assert PENAFIEL_UTILS.analizar_proposito(None) is False
    assert PENAFIEL_UTILS.analizar_proposito("") is False


def test_danone_asunto_nulo_sigue_lanzando_igual_que_antes():
    with pytest.raises(AttributeError):
        DANONE_UTILS.analizar_proposito_regex("hola", None)
    with pytest.raises(AttributeError):
        DANONE_UTILS.analizar_proposito("hola", None)


@pytest.mark.parametrize("cliente", ["holanda", "heineken", "test_holanda", None])
def test_init_sin_gate_por_cuerpo_delega_al_parser(cliente):
    r = regex.gate("x", "gracias", ThreadCtx(etapa=ETAPA_INIT, customer=cliente))
    assert (r.es_os, r.tipo_evento, r.detalle) == (True, NUEVA_SOLICITUD, "delegado_al_parser")


@pytest.mark.parametrize(
    "cuerpo, tipo, detalle",
    [
        ("adjunto la ampliacion", MODIFICAR_FILAS, "excel_upsert"),
        (None, MODIFICAR_FILAS, "excel_upsert"),
        ("BOT.ESTATUS por favor", ESTATUS, "bot.estatus"),
        ("bot.status", ESTATUS, "bot.status"),
        ("bot.ayuda", ESTATUS, "bot.ayuda"),
        ("bot.global", ESTATUS, "bot.global"),
        ("bot.finalizar", ESTATUS, "bot.finalizar"),
        ("bot.cancelar", CANCELAR_SOLICITUD, "bot.cancelar"),
    ],
)
def test_reply_siempre_es_os_y_lee_palabras_bot(cuerpo, tipo, detalle):
    r = regex.gate("RE: x", cuerpo, ThreadCtx(etapa=ETAPA_REPLY, customer="danone", direccion="inbound"))
    assert (r.es_os, r.tipo_evento, r.detalle) == (True, tipo, detalle)


def test_extract_regex_no_devuelve_filas():
    assert regex.extract("cualquier cosa", ThreadCtx(etapa=ETAPA_REPLY)) == []


def test_decidir_por_defecto_es_regex_sin_log(capsys):
    d = classifier.decidir("RE: x", "bot.cancelar", ThreadCtx(etapa=ETAPA_REPLY, customer="danone"))
    assert (d.proveedor_gate, d.proveedor_extract) == ("regex", "regex")
    assert d.tipo_evento == CANCELAR_SOLICITUD
    assert d.rows == () and d.filas_revision == () and d.fallbacks == ()
    assert "[CLASSIFIER]" not in capsys.readouterr().out

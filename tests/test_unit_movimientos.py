"""Pruebas unitarias del propósito del correo: regex de movimientos de Danone y
Penafiel (``config/customers/*/movimientos_*.py``) y las funciones que las
aplican (``analizar_proposito``).

Los bugs conocidos (regex ``\\a``, stopwords antes del regex) NO viven aquí:
están en ``test_known_bugs.py`` como ``xfail(strict=True)``.
"""

import re

import pytest

from config.customers.danone import movimientos_danone as danone
from config.customers.penafiel import movimientos_penafiel as penafiel
from parsers.danone_parse.utils import DANONE_UTILS
from parsers.penafiel_parse.utils import PENAFIEL_UTILS

MODULOS = {"danone": danone, "penafiel": penafiel}


def coincide(patrones, texto):
    return any(re.search(p, texto) for p in patrones)


@pytest.fixture(params=sorted(MODULOS))
def cliente(request):
    return request.param, MODULOS[request.param]


# ---------------------------------------------------------------- listas compiladas
def test_todos_los_patrones_compilan(cliente):
    _, modulo = cliente
    for patrones in (modulo.MOVEMENTS, modulo.CREATE_REQUESTS, modulo.IGNORE_REQUESTS):
        for patron in patrones:
            re.compile(patron)


@pytest.mark.parametrize(
    "texto",
    [
        "instalacion", "instalaciones", "instalación", "instalar", "instalen",
        "retiro", "retiros", "retirar", "retiren",
        "reubicacion", "reubicaciones", "reubicar", "reubiquen",
        "movimiento", "movimientos", "mover", "muevan",
        "traslado", "trasladar", "trasladen",
        "cambio de ubicacion", "cambio de ubicación", "cambiar de ubicacion",
        "alta", "altas", "servicios", "orden de servicio", "ordenes de servicio",
    ],
)
def test_movements_reconoce_el_verbo_o_sustantivo(cliente, texto):
    _, modulo = cliente
    assert coincide(modulo.MOVEMENTS, texto)


@pytest.mark.parametrize(
    "texto",
    ["gracias", "buen dia", "saludos cordiales", "adjunto archivo", "hola equipo"],
)
def test_movements_no_reconoce_texto_neutro(cliente, texto):
    _, modulo = cliente
    assert not coincide(modulo.MOVEMENTS, texto)


@pytest.mark.parametrize(
    "texto",
    [
        "favor de realizar instalaciones",
        "solicito retiro",
        "me apoyan con instalaciones",
        "carga de servicios",
        "primera carga de servicios",
        "orden de servicio",
        "solicito reubicacion",
        "mover los siguientes equipos",
        "movimiento de equipos",
        "cambio de ubicacion",
        "servicios para su atencion",
    ],
)
def test_create_requests_reconoce_peticiones(cliente, texto):
    _, modulo = cliente
    assert coincide(modulo.CREATE_REQUESTS, texto)


@pytest.mark.parametrize(
    "texto",
    [
        "seguimiento", "estatus", "status", "consulta", "consulto", "informo",
        "se realizo", "se realizó", "se atendio", "completado", "completada",
        "finalizado", "cancelada", "cerrado", "evidencia", "validacion", "validación",
    ],
)
def test_ignore_requests_reconoce_correos_de_seguimiento(cliente, texto):
    _, modulo = cliente
    assert coincide(modulo.IGNORE_REQUESTS, texto)


@pytest.mark.parametrize("texto", ["instalaciones", "retiro de equipo", "favor de atender"])
def test_ignore_requests_no_atrapa_peticiones(cliente, texto):
    _, modulo = cliente
    assert not coincide(modulo.IGNORE_REQUESTS, texto)


def test_los_patrones_se_aplican_con_limites_de_palabra(cliente):
    """``\\bretiros?\\b`` no debe disparar con una subcadena de otra palabra."""
    _, modulo = cliente
    assert not coincide(modulo.MOVEMENTS, "autoretiro")
    assert not coincide(modulo.MOVEMENTS, "inaltas")


def test_dic_sabanas_mov_define_movimientos_y_ruta(cliente):
    _, modulo = cliente
    assert set(modulo.DIC_SABANAS_MOV) == {"MOVIMIENTOS", "RUTA"}
    assert {"INSTALACION", "RETIRO", "ALTA"} <= set(modulo.DIC_SABANAS_MOV["MOVIMIENTOS"])
    assert {"REPARACION", "RUTA"} <= set(modulo.DIC_SABANAS_MOV["RUTA"])


def test_traslado_solo_es_tipo_de_servicio_valido_en_penafiel():
    """Hallazgo congelado (okf: 'Traslados en Danone'): ``TRASLADO`` está en
    el diccionario de Penafiel pero no en el de Danone."""
    assert "TRASLADO" in penafiel.DIC_SABANAS_MOV["MOVIMIENTOS"]
    assert "TRASLADO" not in danone.DIC_SABANAS_MOV["MOVIMIENTOS"]


# ---------------------------------------------------------------- analizar_proposito
def danone_proposito(cuerpo, asunto="Solicitud"):
    return DANONE_UTILS.analizar_proposito(cuerpo, asunto)


def penafiel_proposito(cuerpo, asunto="Solicitud"):
    # penafiel.py concatena cuerpo y asunto antes de llamar.
    return PENAFIEL_UTILS.analizar_proposito(f"{cuerpo} {asunto}")


PROPOSITO = {"danone": danone_proposito, "penafiel": penafiel_proposito}


@pytest.mark.parametrize(
    "cuerpo",
    [
        "Favor de realizar las instalaciones de los equipos",
        "Solicito el retiro de un enfriador",
        "Buen dia, requiero un traslado de equipos",
        "Les comparto la carga de servicios",
        "favor de mover los equipos",
        "<p>Favor de <b>programar</b> servicios</p>",
        "Les envio orden de servicio",
    ],
)
def test_proposito_valido(cliente, cuerpo):
    nombre, _ = cliente
    assert PROPOSITO[nombre](cuerpo) is True


@pytest.mark.parametrize(
    "cuerpo",
    [
        "Estatus de mi solicitud de instalación",
        "Seguimiento a retiros",
        "Buen dia, gracias por todo",
        "Solicitud ya cancelada, retiro",
    ],
)
def test_proposito_invalido(cliente, cuerpo):
    nombre, _ = cliente
    assert PROPOSITO[nombre](cuerpo) is False


def test_proposito_toma_en_cuenta_el_asunto_en_danone():
    assert danone_proposito("Buen dia, saludos", asunto="Instalaciones de enfriadores") is True
    assert danone_proposito("Buen dia, saludos", asunto="Hola") is False


def test_proposito_ignora_el_html_en_danone():
    html = "<div><p>Estimados,</p><p>Favor de <b>instalar</b> los equipos.</p></div>"
    assert danone_proposito(html) is True


def test_proposito_sin_cuerpo_en_penafiel():
    assert PENAFIEL_UTILS.analizar_proposito("") is False
    assert PENAFIEL_UTILS.analizar_proposito(None) is False


# ---------------------------------------------------------------- normalización de texto
def test_normalizar_texto_quita_acentos_y_signos():
    assert DANONE_UTILS.normalizar_texto("  ¡Instalación,  RETIRO!  ") == "instalacion retiro"
    assert DANONE_UTILS.normalizar_texto("") == ""
    assert DANONE_UTILS.normalizar_texto(None) == ""


def test_eliminar_stopwords():
    assert DANONE_UTILS.eliminar_stopwords("Favor de realizar la instalación") == "favor realizar instalación"


def test_convertir_html_a_texto_normaliza_y_quita_stopwords():
    assert DANONE_UTILS.convertir_html_a_texto("<p>Favor de <b>instalar</b> los equipos</p>") == "favor instalar equipos"


# ---------------------------------------------------------------- pie de firma «Aviso de privacidad»
CORREO_SIN_SOLICITUD_CON_AVISO_DE_PRIVACIDAD = (
    "Buen dia. Gracias por su mensaje, quedamos atentos.\n\n"
    "Saludos cordiales,\nContacto Ejemplo\n\n"
    "Aviso de privacidad: este mensaje y sus anexos son confidenciales y de uso "
    "exclusivo del destinatario. Si lo recibio por error, eliminelo."
)


def test_pie_de_aviso_de_privacidad_hoy_no_convierte_el_correo_en_movimiento(cliente):
    """Documenta el resultado ACTUAL (a petición de la orquestadora).

    El correo no pide ningún servicio; solo trae un pie «Aviso de privacidad».
    Hoy NO es un propósito válido porque los patrones ``\\avisos`` / ``\\aviso``
    usan ``\\a`` (BEL) y nunca matchean (bug 1 de okf/riesgos/bugs.md).

    ATENCIÓN: al corregir ese bug (``\\b`` en lugar de ``\\a``), ``\\baviso\\b``
    sí matchea «aviso de privacidad» y este correo pasaría a ser un movimiento
    (se verificó con el parche hipotético). Cuando eso ocurra este test se
    pondrá rojo junto con ``test_movements_reconoce_aviso`` (xfail strict): hay
    que decidir si el patrón debe excluir el pie de firma antes de actualizar
    ambos.
    """
    nombre, _ = cliente
    assert PROPOSITO[nombre](CORREO_SIN_SOLICITUD_CON_AVISO_DE_PRIVACIDAD, asunto="Re: Hola") is False

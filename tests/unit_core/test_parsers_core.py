"""parsers/core: única implementación + los módulos originales la re-exportan."""

import asyncio
from types import SimpleNamespace

import duckdb
import pytest

from parsers.core.correo import detectar_tipo_correo
from parsers.core.tablas import unir_tablas
from parsers.core.texto import convertir_html_a_texto, eliminar_stopwords, normalizar_texto
from parsers.danone_parse.reader import DANONE_READER
from parsers.danone_parse.utils import DANONE_UTILS
from parsers.gen_parse.reader import GEN_READER
from parsers.gen_parse.utils import GEN_UTILS
from parsers.penafiel_parse.reader import PENAFIEL_READER
from parsers.penafiel_parse.utils import PENAFIEL_UTILS


@pytest.mark.parametrize("clase", [DANONE_UTILS, GEN_UTILS], ids=["danone", "gen"])
@pytest.mark.parametrize(
    "nombre,fn",
    [
        ("unir_tablas", unir_tablas),
        ("normalizar_texto", normalizar_texto),
        ("eliminar_stopwords", eliminar_stopwords),
        ("convertir_html_a_texto", convertir_html_a_texto),
    ],
)
def test_utils_reexportan_core(clase, nombre, fn):
    assert getattr(clase, nombre) is fn


def test_penafiel_reexporta_unir_tablas():
    assert PENAFIEL_UTILS.unir_tablas is unir_tablas


@pytest.mark.parametrize("clase", [DANONE_READER, GEN_READER, PENAFIEL_READER], ids=["danone", "gen", "penafiel"])
def test_readers_reexportan_detectar_tipo_correo(clase):
    assert clase.detectar_tipo_correo is detectar_tipo_correo


def test_normalizar_texto():
    assert normalizar_texto("  ¡Instalación,  RETIRO!  ") == "instalacion retiro"
    assert normalizar_texto("") == ""
    assert normalizar_texto(None) == ""


def test_eliminar_stopwords_conserva_acentos():
    assert eliminar_stopwords("Favor de realizar la instalación") == "favor realizar instalación"


def test_convertir_html_a_texto_quita_stopwords_antes_de_los_regex():
    # Bug conocido (xfail en test_known_bugs): 'se' desaparece. Se conserva tal cual.
    assert convertir_html_a_texto("<p>Favor de <b>instalar</b> los equipos</p>") == "favor instalar equipos"
    assert convertir_html_a_texto("<p>Se realizó</p>") == "realizo"


def _tabla(con, nombre, columnas, filas):
    cols = ", ".join(f'"{c}" VARCHAR' for c in columnas)
    con.execute(f'CREATE TABLE "{nombre}" ({cols})')
    for fila in filas:
        marcas = ", ".join("?" for _ in fila)
        con.execute(f'INSERT INTO "{nombre}" VALUES ({marcas})', fila)


def test_unir_tablas_vacia():
    assert unir_tablas([], duckdb.connect()) is None


def test_unir_tablas_une_misma_estructura():
    con = duckdb.connect()
    _tabla(con, "t1", ["A", "B"], [("1", "x")])
    _tabla(con, "t2", ["A", "B"], [("2", "y")])
    tablas = [{"table": "t1"}, {"table": "t2"}]
    assert unir_tablas(tablas, con) == "t1"
    assert sorted(con.execute('SELECT * FROM "t1"').fetchall()) == [("1", "x"), ("2", "y")]


def test_unir_tablas_estructura_distinta_regresa_primera_sin_cambios():
    con = duckdb.connect()
    _tabla(con, "t1", ["A", "B"], [("1", "x")])
    _tabla(con, "t2", ["A", "C"], [("2", "y")])
    assert unir_tablas([{"table": "t1"}, {"table": "t2"}], con) == "t1"
    assert con.execute('SELECT * FROM "t1"').fetchall() == [("1", "x")]


def _cliente(adjuntos):
    respuesta = SimpleNamespace(value=[SimpleNamespace(name=n) for n in adjuntos])

    class _Get:
        async def get(self):
            return respuesta

    class _Msg:
        attachments = _Get()

    class _Msgs:
        def by_message_id(self, _):
            return _Msg()

    class _User:
        messages = _Msgs()

    class _Users:
        def by_user_id(self, _):
            return _User()

    return SimpleNamespace(users=_Users())


def _correo(html):
    return SimpleNamespace(unique_body=SimpleNamespace(content=html))


def test_detectar_tipo_correo_excel_y_palabra():
    r = asyncio.run(detectar_tipo_correo(_cliente(["Datos.XLSM"]), "u", "m", _correo("hola BOT.status")))
    assert r == {
        "tiene_excel": True,
        "tiene_palabra_reservada": True,
        "palabra": "bot.status",
        "descripcion": "Dar estatus de la solicitud",
    }


def test_detectar_tipo_correo_sin_nada():
    r = asyncio.run(detectar_tipo_correo(_cliente(["foto.png"]), "u", "m", SimpleNamespace()))
    assert r == {"tiene_excel": False, "tiene_palabra_reservada": False, "palabra": None, "descripcion": None}

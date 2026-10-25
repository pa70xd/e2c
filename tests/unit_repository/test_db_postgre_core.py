"""``DB_POSTGRE`` de Danone, Gen y Penafiel sobre ``repository/core``.

Fija la interfaz (métodos, firmas, constantes) y las diferencias de
comportamiento entre clientes, que la base común no debe borrar. Sin
PostgreSQL: solo se reemplaza ``execute_query`` del módulo del cliente.
"""

import importlib
import inspect
import math
import sys
import types

import pytest
from psycopg2.extras import Json

from tests.sql.test_cooler_sql import REPO_MODULES, cooler

IDS = ["danone", "gen", "penafiel"]

METODOS = {
    "get_available_catalog": "(cliente: str) -> dict[str, list[str]]",
    "save_email_log_init": "(email_model) -> None",
    "consulta_link_email": "(email_model) -> None",
    "email_init_exist": "(mail_id: str) -> bool",
    "send_email_request": "(parametros)",
    "send_email_coolers": "(parametros)",
    "insert_update_cooler": "(parametros)",
    "email_reply_validate": "(conversation_id: str, subject: str)",
    "update_cooler": "(request_code: str, df)",
    "update_email_request": "(request_code: str)",
    "complete_email_request": "(request_code: str) -> str | None",
    "cancel_email_request": "(request_code: str)",
    "get_email_request_status": "(request_code: str) -> str | None",
    "cancel_pending_coolers": "(request_code: str)",
    "get_total_coolers": "(request_code: str) -> int",
    "conversation_exists": "(conversation_id: str) -> bool",
    "email_request_bot_status": "(request_code: str)",
    "get_email_request_global": "()",
    "get_distribuidora_mov": "(cp: str, distribuidora: str) -> dict | None",
    "get_distribuidora_ruta": "(cp: str, distribuidora: str) -> dict | None",
}

CONSTANTES = {
    "DEBUG": False,
    "DB_SCHEMA": "repare_email_parse",
    "EMAILS_LOG_TABLE": "emails_log",
    "EMAIL_REQUEST_TABLE": "email_request",
    "COOLER_REQUEST_TABLE": "cooler_request",
    "EMAILS_LOG": "repare_email_parse.emails_log",
    "EMAIL_REQUEST": "repare_email_parse.email_request",
    "COOLER_REQUEST": "repare_email_parse.cooler_request",
}


def _modulo(nombre):
    return importlib.import_module(nombre)


@pytest.fixture(params=REPO_MODULES, ids=IDS)
def modulo(request):
    return _modulo(request.param)


class Spy:
    def __init__(self, respuesta=None):
        self.calls = []
        self.respuesta = respuesta

    def __call__(self, query, params=()):
        self.calls.append((query, params))
        return self.respuesta


def espiar(monkeypatch, modulo, respuesta=None):
    spy = Spy(respuesta)
    monkeypatch.setattr(modulo, "execute_query", spy)
    return spy


# ---------------------------------------------------------------------------
# Interfaz congelada
# ---------------------------------------------------------------------------

def test_metodos_publicos_y_firmas(modulo):
    publicos = {n: m for n, m in vars(modulo.DB_POSTGRE).items() if not n.startswith("_")}
    assert set(publicos) == set(METODOS)
    for nombre, miembro in publicos.items():
        assert isinstance(miembro, staticmethod), nombre
        assert str(inspect.signature(miembro.__func__)) == METODOS[nombre]


def test_constantes_de_modulo(modulo):
    for nombre, valor in CONSTANTES.items():
        assert getattr(modulo, nombre) == valor, nombre
    for nombre in dir(modulo):
        if nombre.startswith("SQL_"):
            assert getattr(modulo, nombre).exists(), nombre


def test_heineken_y_holanda_siguen_importando_constantes_de_danone():
    danone = _modulo("repository.danone.consultas_postgre")
    for nombre in ("repository.heineken.consultas_postgre", "repository.holanda.consultas_postgre"):
        mod = _modulo(nombre)
        assert mod.COOLER_REQUEST == danone.COOLER_REQUEST
        assert mod.EMAIL_REQUEST == danone.EMAIL_REQUEST


def test_cada_metodo_vive_en_el_modulo_del_cliente(modulo):
    for nombre, miembro in vars(modulo.DB_POSTGRE).items():
        if isinstance(miembro, staticmethod):
            assert miembro.__func__.__globals__ is vars(modulo), nombre
            assert miembro.__func__.__module__ == modulo.__name__, nombre


def test_monkeypatch_de_constantes_del_modulo_aplica(monkeypatch, modulo):
    spy = espiar(monkeypatch, modulo, respuesta=[{"status": "PENDING"}])
    monkeypatch.setattr(modulo, "EMAIL_REQUEST", "esquema_x.email_request")
    assert modulo.DB_POSTGRE.get_email_request_status("REPARE_000001") == "PENDING"
    assert "esquema_x.email_request" in spy.calls[0][0]


def test_las_tres_clases_son_independientes():
    clases = [_modulo(n).DB_POSTGRE for n in REPO_MODULES]
    assert len({id(c) for c in clases}) == 3
    funcs = [vars(c)["update_cooler"].__func__ for c in clases]
    assert len({id(f) for f in funcs}) == 3


def test_subclase_en_modulo_sin_constantes_falla_al_importar():
    from repository.core.consultas_postgre import DBPostgreBase

    mod = types.ModuleType("repository.tmp_sin_constantes")
    sys.modules[mod.__name__] = mod
    try:
        with pytest.raises(ImportError, match="no define"):
            exec("class DB_POSTGRE(Base):\n    pass\n", {"Base": DBPostgreBase, "__name__": mod.__name__})
    finally:
        del sys.modules[mod.__name__]


# ---------------------------------------------------------------------------
# Diferencias de comportamiento entre clientes (overrides)
# ---------------------------------------------------------------------------

# insert_update_cooler: Gen y Penafiel usan la columna "serie" como
# serie_dnn_bnf cuando viene; Danone la ignora.
SERIE_ESPERADA = {"danone": "DNN-0001", "gen": "SERIE-9", "penafiel": "SERIE-9"}


@pytest.mark.parametrize("nombre,cliente", zip(REPO_MODULES, IDS), ids=IDS)
def test_insert_update_cooler_columna_serie(monkeypatch, nombre, cliente):
    mod = _modulo(nombre)
    spy = espiar(monkeypatch, mod)
    mod.DB_POSTGRE.insert_update_cooler(dict(cooler(1, "FAB-0001", "DNN-0001"), serie="SERIE-9"))

    (update_q, update_p), (insert_q, insert_p) = spy.calls
    assert update_p[3:5] == ("FAB-0001", SERIE_ESPERADA[cliente])
    assert insert_p[5:7] == ("FAB-0001", SERIE_ESPERADA[cliente])
    assert insert_p[-2:] == ("FAB-0001", SERIE_ESPERADA[cliente])


@pytest.mark.parametrize("serie", [None, float("nan")], ids=["none", "nan"])
def test_insert_update_cooler_sin_serie_igual_en_todos(monkeypatch, modulo, serie):
    spy = espiar(monkeypatch, modulo)
    modulo.DB_POSTGRE.insert_update_cooler(dict(cooler(1, 123, float("nan")), serie=serie))
    _, update_p = spy.calls[0]
    assert update_p[3:5] == ("123", None)


def test_insert_update_cooler_serie_numerica_se_vuelve_texto(monkeypatch):
    for nombre in REPO_MODULES[1:]:
        mod = _modulo(nombre)
        spy = espiar(monkeypatch, mod)
        mod.DB_POSTGRE.insert_update_cooler(dict(cooler(1, "FAB", "DNN"), serie=42))
        assert spy.calls[0][1][4] == "42"


def test_insert_update_cooler_no_inserta_si_el_update_devolvio_filas(monkeypatch, modulo):
    spy = espiar(monkeypatch, modulo, respuesta=[{"request_code": "REPARE_000001", "row_number": 1}])
    assert modulo.DB_POSTGRE.insert_update_cooler(cooler(1, "FAB", "DNN")) == spy.respuesta
    assert len(spy.calls) == 1


def test_insert_update_cooler_loguea_si_no_inserta(monkeypatch, modulo, capsys):
    espiar(monkeypatch, modulo, respuesta=[])
    assert modulo.DB_POSTGRE.insert_update_cooler(cooler(3, "FAB", "DNN")) == []
    assert "requiere revisión: request_code=REPARE_000001 row_number=3" in capsys.readouterr().out


# get_distribuidora_*: una fila sin "distribuidora" se descarta (None) o se
# devuelve tal cual, según el cliente.
FILA_SIN_DISTRIBUIDORA = [{"distribuidora": None, "precio": 10}]
DESCARTA_SIN_DISTRIBUIDORA = {
    ("danone", "get_distribuidora_mov"): True,
    ("danone", "get_distribuidora_ruta"): True,
    ("gen", "get_distribuidora_mov"): True,
    ("gen", "get_distribuidora_ruta"): False,
    ("penafiel", "get_distribuidora_mov"): False,
    ("penafiel", "get_distribuidora_ruta"): False,
}


@pytest.mark.parametrize("cliente,metodo", sorted(DESCARTA_SIN_DISTRIBUIDORA), ids=lambda v: v)
def test_distribuidora_fila_sin_distribuidora(monkeypatch, cliente, metodo):
    mod = _modulo(f"repository.{cliente}.consultas_postgre")
    espiar(monkeypatch, mod, respuesta=FILA_SIN_DISTRIBUIDORA)
    resultado = getattr(mod.DB_POSTGRE, metodo)(" 01000 ", " DIST ")
    esperado = None if DESCARTA_SIN_DISTRIBUIDORA[(cliente, metodo)] else FILA_SIN_DISTRIBUIDORA[0]
    assert resultado == esperado


@pytest.mark.parametrize("metodo", ["get_distribuidora_mov", "get_distribuidora_ruta"])
def test_distribuidora_igual_en_todos(monkeypatch, modulo, metodo):
    spy = espiar(monkeypatch, modulo, respuesta=[{"distribuidora": "D1"}])
    assert getattr(modulo.DB_POSTGRE, metodo)(" 01000 ", " DIST ") == {"distribuidora": "D1"}
    # mov limpia la distribuidora; ruta la manda tal cual.
    esperado = ("01000", "DIST") if metodo.endswith("mov") else ("01000", " DIST ")
    assert spy.calls[0][1] == esperado
    spy.respuesta = []
    assert getattr(modulo.DB_POSTGRE, metodo)("01000", "DIST") is None
    assert getattr(modulo.DB_POSTGRE, metodo)("  ", "DIST") is None
    assert len(spy.calls) == 2


def test_distribuidora_mov_sin_distribuidora_no_consulta(monkeypatch, modulo):
    spy = espiar(monkeypatch, modulo)
    assert modulo.DB_POSTGRE.get_distribuidora_mov("01000", "  ") is None
    assert spy.calls == []


# ---------------------------------------------------------------------------
# Métodos comunes: mismo SQL y mismos parámetros en los tres
# ---------------------------------------------------------------------------

class Email:
    def __init__(self):
        for i, campo in enumerate(
            "graph_message_id internet_message_id conversation_id conversation_index parent_message_id "
            "change_key direction sender_name sender_email subject body has_attachments attachment_count "
            "processing_status processing_message received_at sent_at customer link_email".split()
        ):
            setattr(self, campo, f"v{i}")
        self.recipients_to, self.recipients_cc, self.recipients_bcc = ["a"], [], []


def _normaliza(valor):
    if isinstance(valor, float) and math.isnan(valor):
        return "<NaN>"
    if isinstance(valor, Json):
        return ("Json", repr(valor.adapted))
    return repr(valor)


def _llamadas_comunes(mod, monkeypatch):
    import pandas as pd

    salida = {}
    casos = {
        "save_email_log_init": ((Email(),), [{"request_code": "R1"}]),
        "consulta_link_email": ((Email(),), [{"request_code": "R1"}]),
        "email_init_exist": (("m1",), [{"exists_email": True}]),
        "send_email_request": ((dict.fromkeys(
            "request_code customer status priority total_coolers pending_coolers completed_coolers "
            "failed_coolers assigned_to".split(), "x"),), [{"request_code": "R1"}]),
        "send_email_coolers": ((cooler(1, float("nan"), 7),), [{"id": 1}]),
        "email_reply_validate": (("c1", "asunto"), [{"request_code": "R1"}]),
        "update_cooler": (("R1", pd.DataFrame([{"status": "ACCEPTED", "os": "1", "serial_number": "F", "serial_dnn": ""}])), [{"id": 1}]),
        "update_email_request": (("R1",), [{"ok": 1}]),
        "complete_email_request": (("R1",), [{"request_code": "R1"}]),
        "cancel_email_request": (("R1",), [{"request_code": "R1"}]),
        "get_email_request_status": (("R1",), [{"status": "COMPLETED"}]),
        "cancel_pending_coolers": (("R1",), [{"id": 1}]),
        "get_total_coolers": (("R1",), [{"total": 3}]),
        "conversation_exists": (("c1",), [{"exists_conversation": False}]),
        "email_request_bot_status": (("R1",), [{"status": "PENDING"}]),
        "get_email_request_global": ((), [{"total": 1}]),
    }
    for metodo, (args, respuesta) in casos.items():
        spy = espiar(monkeypatch, mod, respuesta=respuesta)
        resultado = getattr(mod.DB_POSTGRE, metodo)(*args)
        params = [tuple(_normaliza(p) for p in c[1]) for c in spy.calls]
        salida[metodo] = (repr(resultado), [c[0] for c in spy.calls], params)
    return salida


def test_metodos_comunes_identicos_en_los_tres(monkeypatch):
    danone, gen, penafiel = (_llamadas_comunes(_modulo(n), monkeypatch) for n in REPO_MODULES)
    assert danone == gen == penafiel
    assert danone["get_email_request_status"][0] == "'COMPLETED'"
    assert danone["conversation_exists"][0] == "False"

"""Matriz comando x cliente de bot/commands.py con dobles mínimos (sin
FakeRepo ni Graph): orden de llamadas al repositorio, mensaje y manejo de
errores, incluidos los caminos que los goldens no cubren."""

import asyncio

import pytest

from bot import commands
from bot.perfiles import perfil_danone, perfil_heineken, perfil_holanda, perfil_penafiel


class Registro:
    """Repositorio/mensajes/process falsos: cada método devuelve lo configurado
    (o lanza si es una excepción) y anota (objeto, método, args)."""

    def __init__(self, nombre, calls, **respuestas):
        self._nombre, self._calls, self._respuestas = nombre, calls, respuestas

    def __getattr__(self, metodo):
        def fn(*args):
            self._calls.append((self._nombre, metodo, args))
            r = self._respuestas.get(metodo, f"{metodo}{args}")
            if isinstance(r, Exception):
                raise r
            return r
        return fn


def _correr(perfil, palabra, resolver):
    tipo = {"tiene_palabra_reservada": palabra is not None, "palabra": palabra}
    return asyncio.run(commands.ejecutar(perfil, tipo, resolver))


def _armar(cliente, calls, db=None, extra=None):
    msj = Registro("msj", calls)
    process = Registro("process", calls)
    db = Registro("db", calls, **(db or {}))
    if cliente in ("danone", "penafiel"):
        fabrica = perfil_danone if cliente == "danone" else perfil_penafiel
        return fabrica(db, msj, process), db, msj
    otro = Registro(f"db_{cliente}", calls, **(extra or {}))
    fabrica = perfil_holanda if cliente == "holanda" else perfil_heineken
    return fabrica(db, otro, msj, process), otro, msj


HILO = ["danone", "penafiel"]
FOLIO = ["holanda", "heineken"]
TODOS = HILO + FOLIO


@pytest.mark.parametrize("cliente", TODOS)
def test_sin_palabra_reservada_no_responde(cliente):
    calls = []
    perfil, _, _ = _armar(cliente, calls)
    assert _correr(perfil, None, commands.solicitud_fija("R1")) is None
    assert calls == []


def test_lectura_estricta_solo_danone_y_penafiel():
    calls = []
    for cliente in HILO:
        perfil, _, _ = _armar(cliente, calls)
        with pytest.raises(KeyError):
            asyncio.run(commands.ejecutar(perfil, {}, commands.solicitud_fija("R1")))
    for cliente in FOLIO:
        perfil, _, _ = _armar(cliente, calls)
        assert asyncio.run(commands.ejecutar(perfil, {}, commands.solicitud_fija("R1"))) is None


@pytest.mark.parametrize("cliente", TODOS)
@pytest.mark.parametrize("palabra", ["bot.help", "BOT.AYUDA"])
def test_ayuda_no_resuelve_solicitud(cliente, palabra):
    calls = []
    perfil, _, _ = _armar(cliente, calls)

    async def no_llamar():
        raise AssertionError("ayuda no debe resolver solicitud")

    r = _correr(perfil, palabra, no_llamar)
    assert r == {"mensaje": "msj_ayuda()", "attachments": None}
    assert calls == [("msj", "msj_ayuda", ())]


@pytest.mark.parametrize("cliente,repo,metodo", [
    ("danone", "db", "get_email_request_global"),
    ("penafiel", "db", "get_email_request_global"),
    ("holanda", "db_holanda", "global_status"),
    ("heineken", "db_heineken", "global_status"),
])
def test_global(cliente, repo, metodo):
    calls = []
    perfil, _, _ = _armar(cliente, calls)
    r = _correr(perfil, "bot.global", None)
    datos = f"{metodo}()"
    assert calls == [
        (repo, metodo, ()),
        ("process", "process_email_request_global", (datos,)),
        ("msj", "msj_global", ()),
    ]
    assert r == {"mensaje": "msj_global()", "attachments": [f"process_email_request_global{(datos,)}"]}


@pytest.mark.parametrize("cliente,metodo,log", [
    ("danone", "get_email_request_global", "[ERROR] No se logró generar el estado global: caida"),
    ("holanda", "global_status", "[HOLANDA][BOT][ERROR] No se logró generar el estado global: caida"),
    ("heineken", "global_status", "[HEINEKEN][BOT][ERROR] No se logró generar el estado global: caida"),
])
def test_global_error_responde_sin_adjunto(cliente, metodo, log, capsys):
    calls = []
    respuestas = {metodo: RuntimeError("caida")}
    perfil, _, _ = _armar(cliente, calls, db=respuestas, extra=respuestas)
    assert _correr(perfil, "bot.global", None) == {"mensaje": "msj_global()", "attachments": None}
    assert log in capsys.readouterr().out


@pytest.mark.parametrize("cliente", TODOS)
def test_global_vacio_sin_adjunto(cliente):
    calls = []
    vacio = {"get_email_request_global": [], "global_status": []}
    perfil, _, _ = _armar(cliente, calls, db=vacio, extra=vacio)
    assert _correr(perfil, "bot.global", None) == {"mensaje": "msj_global()", "attachments": None}
    assert not any(c[1] == "process_email_request_global" for c in calls)


@pytest.mark.parametrize("cliente", TODOS)
def test_comando_no_reconocido(cliente):
    # Inalcanzable desde el reader (solo detecta palabras_reservadas), se conserva.
    calls = []
    perfil, _, _ = _armar(cliente, calls)
    r = _correr(perfil, "bot.otra", None)
    assert r == {"mensaje": "msj_comando_no_reconocido()", "attachments": None}


@pytest.mark.parametrize("cliente,repo,metodo", [
    ("danone", "db", "email_request_bot_status"),
    ("penafiel", "db", "email_request_bot_status"),
    ("holanda", "db_holanda", "bot_status"),
    ("heineken", "db_heineken", "bot_status"),
])
@pytest.mark.parametrize("palabra", ["bot.estatus", "bot.status"])
def test_estatus(cliente, repo, metodo, palabra):
    calls = []
    perfil, _, _ = _armar(cliente, calls)
    r = _correr(perfil, palabra, commands.solicitud_fija("R1"))
    assert calls == [(repo, metodo, ("R1",)), ("msj", "msj_status_solicitud", (f"{metodo}('R1',)",))]
    assert r["attachments"] is None


@pytest.mark.parametrize("cliente,vacio", [
    ("danone", ("msj_fail", ())),
    ("penafiel", ("msj_fail", ())),
    ("holanda", ("msj_folio_requerido", ("REPARE_9",))),       # folio escrito
    ("heineken", ("msj_folio_requerido", ("R1",))),            # request_code
])
@pytest.mark.parametrize("falla", [None, RuntimeError("caida")])
def test_estatus_vacio_o_error(cliente, vacio, falla, capsys):
    calls = []
    resp = {"email_request_bot_status": falla, "bot_status": falla}
    perfil, _, _ = _armar(cliente, calls, db=resp, extra=resp)

    async def resolver():
        return commands.Solicitud("R1", "REPARE_9")

    r = _correr(perfil, "bot.estatus", resolver)
    assert calls[-1] == ("msj",) + vacio
    assert r["mensaje"] == f"{vacio[0]}{vacio[1]}"
    salida = capsys.readouterr().out
    if falla:
        esperado = {
            "danone": "No se logro cancelar la solicitud caida",
            "penafiel": "No se logro cancelar la solicitud caida",
            "holanda": "[HOLANDA][BOT][ERROR] No se logró consultar el estatus de R1: caida",
            "heineken": "[HEINEKEN][BOT][ERROR] No se logró consultar el estatus de R1: caida",
        }[cliente]
        assert esperado in salida


@pytest.mark.parametrize("cliente", TODOS)
def test_cancelar(cliente):
    calls = []
    perfil, _, _ = _armar(cliente, calls)
    r = _correr(perfil, "bot.cancelar", commands.solicitud_fija("R1"))
    assert calls == [
        ("db", "cancel_pending_coolers", ("R1",)),
        ("db", "cancel_email_request", ("R1",)),
        ("msj", "msj_cancelar", ("R1",)),
    ]
    assert r == {"mensaje": "msj_cancelar('R1',)", "attachments": None}


@pytest.mark.parametrize("cliente,log", [
    ("danone", "No se logro cancelar la solicitud caida"),
    ("holanda", "[HOLANDA][BOT][ERROR] No se logró cancelar R1: caida"),
    ("heineken", "[HEINEKEN][BOT][ERROR] No se logró cancelar R1: caida"),
])
def test_cancelar_error_corta_y_responde_exito(cliente, log, capsys):
    calls = []
    perfil, _, _ = _armar(cliente, calls, db={"cancel_pending_coolers": RuntimeError("caida")})
    r = _correr(perfil, "bot.cancelar", commands.solicitud_fija("R1"))
    assert [c[1] for c in calls] == ["cancel_pending_coolers", "msj_cancelar"]
    assert r["mensaje"] == "msj_cancelar('R1',)"
    assert log in capsys.readouterr().out


@pytest.mark.parametrize("cliente", TODOS)
@pytest.mark.parametrize("palabra", ["bot.finalizar", "bot.cerrar"])
def test_finalizar(cliente, palabra):
    calls = []
    perfil, _, _ = _armar(cliente, calls)
    r = _correr(perfil, palabra, commands.solicitud_fija("R1"))
    assert calls == [("db", "complete_email_request", ("R1",)), ("msj", "msj_finalizar", ("R1",))]
    assert r == {"mensaje": "msj_finalizar('R1',)", "attachments": None}


@pytest.mark.parametrize("cliente,log", [
    ("penafiel", "No se logro completar la solicitud caida"),
    ("holanda", "[HOLANDA][BOT][ERROR] No se logró finalizar R1: caida"),
    ("heineken", "[HEINEKEN][BOT][ERROR] No se logró finalizar R1: caida"),
])
def test_finalizar_error_responde_exito(cliente, log, capsys):
    calls = []
    perfil, _, _ = _armar(cliente, calls, db={"complete_email_request": RuntimeError("caida")})
    r = _correr(perfil, "bot.finalizar", commands.solicitud_fija("R1"))
    assert r["mensaje"] == "msj_finalizar('R1',)"
    assert log in capsys.readouterr().out


# --- resolver_por_folio (Holanda siempre; Heineken cuando no hay hilo) ---

def _folio(calls, folio, solicitud):
    async def buscar():
        calls.append(("graph", "folio", ()))
        return folio

    def get_request(f):
        calls.append(("db_x", "get_request", (f,)))
        return solicitud

    return commands.resolver_por_folio(buscar, get_request, Registro("msj", calls))


@pytest.mark.parametrize("cliente", FOLIO)
def test_sin_folio_pide_folio(cliente):
    calls = []
    perfil, _, _ = _armar(cliente, calls)
    r = _correr(perfil, "bot.cancelar", _folio(calls, None, None))
    assert calls == [("graph", "folio", ()), ("msj", "msj_folio_requerido", ())]
    assert r == {"mensaje": "msj_folio_requerido()", "attachments": None}


@pytest.mark.parametrize("cliente", FOLIO)
def test_folio_inexistente(cliente):
    calls = []
    perfil, _, _ = _armar(cliente, calls)
    r = _correr(perfil, "bot.finalizar", _folio(calls, "REPARE_9", None))
    assert calls[-1] == ("msj", "msj_folio_requerido", ("REPARE_9",))
    assert not any(c[1] == "complete_email_request" for c in calls)
    assert r["mensaje"] == "msj_folio_requerido('REPARE_9',)"


@pytest.mark.parametrize("cliente", FOLIO)
def test_folio_resuelto_usa_request_code_de_la_solicitud(cliente):
    calls = []
    perfil, _, _ = _armar(cliente, calls)
    r = _correr(perfil, "bot.cancelar", _folio(calls, "REPARE_9", {"request_code": "REPARE_000009"}))
    assert calls == [
        ("graph", "folio", ()),
        ("db_x", "get_request", ("REPARE_9",)),
        ("db", "cancel_pending_coolers", ("REPARE_000009",)),
        ("db", "cancel_email_request", ("REPARE_000009",)),
        ("msj", "msj_cancelar", ("REPARE_000009",)),
    ]
    assert r["mensaje"] == "msj_cancelar('REPARE_000009',)"


@pytest.mark.parametrize("palabra", ["bot.help", "bot.global", "bot.otra"])
def test_folio_no_se_busca_si_el_comando_no_lo_necesita(palabra):
    calls = []
    perfil, _, _ = _armar("holanda", calls)
    _correr(perfil, palabra, _folio(calls, "REPARE_9", {"request_code": "R"}))
    assert ("graph", "folio", ()) not in calls

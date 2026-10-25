"""Bugs conocidos de ``okf/riesgos/bugs.md`` congelados como ``xfail(strict=True)``.

Cada prueba afirma el comportamiento CORRECTO. Hoy falla (``xfail``). Cuando
alguien corrija el bug la prueba pasa, ``strict=True`` la vuelve ROJA (XPASS) y
obliga a quitar el ``xfail`` y a revisar los goldens afectados
(``pytest --update-golden`` + revisar el diff).
"""

import asyncio
import importlib
import math
import re

import pytest

from config.customers.danone import movimientos_danone
from config.customers.penafiel import movimientos_penafiel
from infrastructure.database.engine_duck import DuckEngine
from parsers.danone_parse.utils import DANONE_UTILS
from src.email_type import EMAIL_TYPE
from tests.support.emails import CLIENTES, MAILBOXES, REPARE, make_email
from tests.support.scenarios import bot_command, inbound

# ---------------------------------------------------------------------------
# Bug 1 — regex con ``\a`` (BEL) en movimientos_danone.py / movimientos_penafiel.py
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=True, reason="bug 1 de okf/riesgos/bugs.md: `\\avisos`/`\\aviso` usan \\a (BEL), nunca matchean")
@pytest.mark.parametrize("modulo", [movimientos_danone, movimientos_penafiel], ids=["danone", "penafiel"])
@pytest.mark.parametrize("texto", ["avisos", "aviso"])
def test_movements_reconoce_aviso(modulo, texto):
    assert any(re.search(patron, texto) for patron in modulo.MOVEMENTS)


@pytest.mark.xfail(
    strict=True,
    reason="bug 'Stopwords antes del regex' (reportado) de okf/riesgos/bugs.md: Danone quita 'se' y deja de ignorar 'se realizó'",
)
def test_danone_ignora_correos_de_confirmacion_con_stopwords():
    # IGNORE_REQUESTS tiene r"\bse realiz[oó]\b", pero convertir_html_a_texto
    # elimina 'se' antes de evaluar los patrones.
    assert DANONE_UTILS.analizar_proposito("Se realizó la instalación", "Hola") is False


# ---------------------------------------------------------------------------
# Bug «NaN a PostgreSQL» — send_email_coolers usa valores crudos
# ---------------------------------------------------------------------------

COOLER_KEYS = (
    "request_code row_number id_cliente fecha_solicitud modelo serie_fabricante serie_dnn_bnf "
    "tipo_servicio canal region plaza razon_social direccion cp ciudad colonia latitud longitud ruta "
    "telefono_1 telefono_2 comentarios cbu cliente os status rejection_reason prioridad folio "
    "ticket_solicitud assigned_to gestion_observaciones fecha_asignacion fecha_atencion fecha_completado"
).split()


def cooler(**overrides):
    base = dict.fromkeys(COOLER_KEYS)
    base.update(request_code="REPARE_000001", row_number=1, status="PENDING", id_cliente="1000001")
    base.update(overrides)
    return base


def has_nan(valores):
    return any(isinstance(v, float) and math.isnan(v) for v in valores)


@pytest.fixture
def sql_spy(monkeypatch):
    """Sustituye ``execute_query`` de un módulo de repositorio y registra los SQL.

    Simula a Postgres: un ``UPDATE`` solo devuelve filas si el SQL trae RETURNING."""

    class Spy:
        def __init__(self):
            self.calls: list[dict] = []

        def install(self, module_name):
            module = importlib.import_module(module_name)

            def fake(query, params=()):
                tipo = query.lstrip().split(None, 1)[0].upper()
                self.calls.append({"tipo": tipo, "query": query, "params": params})
                if tipo == "UPDATE" and "RETURNING" in query.upper():
                    return [{"request_code": "REPARE_000001"}]
                return None

            monkeypatch.setattr(module, "execute_query", fake)
            return module

    return Spy()


REPO_MODULES = [
    "repository.danone.consultas_postgre",
    "repository.gen.consultas_postgre",
    "repository.penafiel.consultas_postgre",
]


# Corregido: send_email_coolers manda las series limpias (NaN -> None).
@pytest.mark.parametrize("modulo", REPO_MODULES, ids=["danone", "gen", "penafiel"])
def test_send_email_coolers_no_manda_nan(sql_spy, modulo):
    repo = sql_spy.install(modulo)
    repo.DB_POSTGRE.send_email_coolers(
        cooler(serie_fabricante=float("nan"), serie_dnn_bnf=float("nan"))
    )
    (llamada,) = sql_spy.calls
    assert not has_nan(llamada["params"])


# ---------------------------------------------------------------------------
# Bug 3 — insert_update_cooler nunca detecta que el UPDATE tocó la fila
# ---------------------------------------------------------------------------

@pytest.mark.xfail(
    strict=True,
    reason="bug 3 de okf/riesgos/bugs.md: email_update_cooler.sql no tiene RETURNING; siempre inserta",
)
@pytest.mark.parametrize("modulo", ["repository.danone.consultas_postgre", "repository.penafiel.consultas_postgre"], ids=["danone", "penafiel"])
def test_insert_update_cooler_no_inserta_si_actualizo(sql_spy, modulo):
    repo = sql_spy.install(modulo)
    repo.DB_POSTGRE.insert_update_cooler(cooler(serie_fabricante="FAB-0001", serie_dnn_bnf="DNN-0001"))
    assert [c["tipo"] for c in sql_spy.calls] == ["UPDATE"]


# ---------------------------------------------------------------------------
# Bug 5 — bot.cancelar no cancelaba coolers pendientes (corregido en Danone y Penafiel)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("cliente", ["danone", "penafiel"])
def test_bot_cancelar_cancela_coolers_pendientes(harness, fixtures_for, cliente):
    fx = fixtures_for(cliente)
    asunto = fx.correos.get("bot", fx.correos.get("outbound"))["subject"]
    msg = bot_command(cliente, asunto, "bot.cancelar", f"msg-bug5-{cliente}", f"conv-bug5-{cliente}")
    harness.deliver(msg)
    nombres = harness.repo.names()
    assert "cancel_pending_coolers" in nombres
    assert nombres.index("cancel_pending_coolers") < nombres.index("cancel_email_request")


# ---------------------------------------------------------------------------
# Bug 6 — detect_direccion puede devolver None y service.py desempaqueta
# ---------------------------------------------------------------------------

def _correo_con_repare_solo_en_copia():
    """Cliente -> otra persona, con el buzón de REPARE únicamente en CC."""
    return make_email(
        subject="RE: Solicitud de servicios REPARE 02/03/2026",
        body="Adjunto comentarios.",
        sender=CLIENTES["danone"],
        to=["otra.persona@example.com"],
        cc=[REPARE["danone"]],
        conversation_id="conv-bug6",
        message_id="msg-bug6",
    )


@pytest.mark.xfail(strict=True, reason="bug 6 de okf/riesgos/bugs.md: detect_direccion devuelve None (EMAIL_TYPE)")
def test_detect_direccion_nunca_devuelve_none(tmp_path):
    import json

    config = tmp_path / "m.json"
    config.write_text(json.dumps(MAILBOXES), encoding="utf-8")
    assert EMAIL_TYPE(config_path=str(config)).detect_direccion(_correo_con_repare_solo_en_copia()) is not None


@pytest.mark.xfail(strict=True, reason="bug 6 de okf/riesgos/bugs.md: service.py:245 desempaqueta None y revienta")
def test_process_mail_no_revienta_con_direccion_none(harness):
    harness.deliver(_correo_con_repare_solo_en_copia())


# ---------------------------------------------------------------------------
# Bug 7 — bot.estatus de Danone/Penafiel: `data` sin asignar si la consulta falla (corregido)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("cliente, modulo, clase", [
    ("danone", "parsers.danone", "DANONE_REPLY"),
    ("penafiel", "parsers.penafiel", "PENAFIEL_REPLY"),
])
def test_bot_estatus_no_lanza_unbound_local_error(harness, cliente, modulo, clase):
    harness.repo.fail("email_request_bot_status", RuntimeError("db caida"))
    msg = bot_command(cliente, "RE: Solicitud", "bot.estatus", f"msg-bug7-{cliente}", "conv-bug7")
    harness.graph.add_message(msg)
    parser = getattr(importlib.import_module(modulo), clase)(DuckEngine.get())
    try:
        asyncio.run(parser.parse(harness.graph, "user-0001", msg.id, msg, "reply_to_bot", cliente, REPARE[cliente]))
    except UnboundLocalError as exc:
        pytest.fail(f"UnboundLocalError: {exc}")

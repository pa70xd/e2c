"""Integración en src/service.py con el pipeline completo del harness.

* Un proveedor externo que falla cae a regex: el resultado es idéntico al
  golden (se compara en solo lectura, aun con ``--update-golden``).
* Un gate externo que dice ``no_os`` corta el hilo y el init de Holanda o
  Heineken antes del parser; los comandos ``bot.*`` siguen.
"""

import pytest

from classifier.contracts import GateResult
from src import service
from tests.conftest import Golden
from tests.support.scenarios import bot_command, inbound

LECTOR = Golden(update=False)

ESCENARIOS = [
    ("danone", "init", "solicitud_servicios.xlsx", "conv-danone-001", "danone_correo_nuevo_con_excel"),
    ("danone", "sin_proposito", "solicitud_servicios.xlsx", "conv-danone-002", "danone_correo_nuevo_sin_proposito"),
    ("danone", "inbound", "ampliacion_servicios.xlsx", "conv-danone-001", "danone_hilo_inbound_con_excel"),
    ("penafiel", "init", "solicitud_servicios.xlsx", "conv-penafiel-001", "penafiel_correo_nuevo_con_excel"),
    ("penafiel", "inbound", "ampliacion_servicios.xlsx", "conv-penafiel-001", "penafiel_hilo_inbound_con_excel"),
    ("holanda", "init", "Casos REPARE 02032026.xlsx", "conv-holanda-001", "holanda_correo_nuevo_con_excel"),
    ("heineken", "d2d_init", "precarga_d2d.xlsx", "conv-heineken-d2d-001", "heineken_d2d_correo_nuevo_con_excel"),
]
MESSAGE_IDS = {
    "danone_correo_nuevo_con_excel": "msg-danone-init",
    "danone_correo_nuevo_sin_proposito": "msg-danone-sinprop",
    "danone_hilo_inbound_con_excel": "msg-danone-in",
    "penafiel_correo_nuevo_con_excel": "msg-penafiel-init",
    "penafiel_hilo_inbound_con_excel": "msg-penafiel-in",
    "holanda_correo_nuevo_con_excel": "msg-holanda-init",
    "heineken_d2d_correo_nuevo_con_excel": "msg-hnk-d2d-init",
}


def _entregar(harness, fixtures_for, cliente, correo, excel, conv, nombre):
    fx = fixtures_for(cliente)
    msg = inbound(cliente, fx.correos[correo], MESSAGE_IDS[nombre], conv)
    return harness.deliver(msg, [fx.xlsx(excel)])


@pytest.mark.parametrize("cliente, correo, excel, conv, nombre", ESCENARIOS, ids=[e[-1] for e in ESCENARIOS])
def test_proveedor_externo_que_falla_da_el_mismo_golden(
    harness, fixtures_for, proveedores, capsys, cliente, correo, excel, conv, nombre
):
    def gate(*a):
        raise RuntimeError("caido")

    def extract(*a):
        raise RuntimeError("caido")

    proveedores.registrar("fake", gate=gate, extract=extract)
    proveedores.redactor()
    proveedores.usar(gate="fake", extract="fake")
    _entregar(harness, fixtures_for, cliente, correo, excel, conv, nombre)
    assert "fallbacks=['gate:fake:RuntimeError'" in capsys.readouterr().out
    LECTOR.check(nombre, harness.snapshot())


@pytest.mark.parametrize("cliente, correo, excel, conv, nombre", ESCENARIOS, ids=[e[-1] for e in ESCENARIOS])
def test_sin_redaccion_da_el_mismo_golden(harness, fixtures_for, proveedores, cliente, correo, excel, conv, nombre):
    """Si la redacción falla, nada sale del proceso."""
    llamadas = []
    proveedores.registrar("fake", gate=lambda *a: llamadas.append(a), extract=lambda *a: llamadas.append(a))
    proveedores.sin_redaccion()
    proveedores.usar(gate="fake", extract="fake")
    _entregar(harness, fixtures_for, cliente, correo, excel, conv, nombre)
    assert llamadas == []
    LECTOR.check(nombre, harness.snapshot())


def _no_os(proveedores):
    proveedores.registrar("fake", gate=lambda s, b, c: GateResult(False, "no_os", 0.95))
    proveedores.redactor()
    proveedores.usar(gate="fake")


def test_hilo_no_os_no_llega_al_parser(harness, fixtures_for, proveedores):
    _no_os(proveedores)
    fx = fixtures_for("danone")
    msg = inbound("danone", fx.correos["inbound"], "msg-danone-in", "conv-danone-001")
    assert harness.deliver(msg, [fx.xlsx("ampliacion_servicios.xlsx")]) is None
    assert "email_reply_validate" not in harness.repo.names()
    assert "insert_update_cooler" not in harness.repo.names()
    assert harness.replies == []


@pytest.mark.parametrize("cliente, correo, excel", [
    ("holanda", "init", "Casos REPARE 02032026.xlsx"),
    ("heineken", "d2d_init", "precarga_d2d.xlsx"),
])
def test_init_holanda_heineken_no_os_no_llega_al_parser(harness, fixtures_for, proveedores, cliente, correo, excel):
    _no_os(proveedores)
    fx = fixtures_for(cliente)
    msg = inbound(cliente, fx.correos[correo], f"msg-{cliente}-x", f"conv-{cliente}-x")
    assert harness.deliver(msg, [fx.xlsx(excel)]) is None
    assert harness.replies == []
    assert "save_email_log_init" not in harness.repo.names()


def test_init_danone_no_os_lo_decide_analizar_proposito(harness, fixtures_for, proveedores):
    _no_os(proveedores)
    fx = fixtures_for("danone")
    msg = inbound("danone", fx.correos["init"], "msg-danone-init", "conv-danone-001")
    harness.deliver(msg, [fx.xlsx("solicitud_servicios.xlsx")])
    assert harness.replies == []
    assert "save_email_log_init" not in harness.repo.names()


def test_comando_bot_sigue_aunque_el_gate_diga_no_os(harness, fixtures_for, proveedores, golden):
    _no_os(proveedores)
    fx = fixtures_for("danone")
    msg = bot_command("danone", fx.correos["bot"]["subject"], fx.correos["comandos"]["ayuda"],
                      "msg-danone-bot-ayuda", "conv-danone-001")
    harness.deliver(msg)
    LECTOR.check("danone_hilo_bot_ayuda", harness.snapshot())


def test_error_del_clasificador_no_corta_el_flujo(monkeypatch):
    import classifier

    def roto(*a, **k):
        raise ValueError("x")

    monkeypatch.setattr(classifier, "decidir_correo", roto)
    assert service.classifier_gate(object(), "holanda", "init") == (True, None)


def test_la_decision_viaja_en_el_parser(harness, fixtures_for, proveedores, monkeypatch):
    """Sin estado global: cada parser recibe la Decision de su correo."""
    from parsers.danone import DANONE_REPLY
    from parsers.holanda import HOLANDA_INIT

    vistas = []
    for clase in (DANONE_REPLY, HOLANDA_INIT):
        original = clase.parse

        async def parse(self, *a, _original=original, **k):
            vistas.append(self.classifier_decision)
            return await _original(self, *a, **k)

        monkeypatch.setattr(clase, "parse", parse)

    proveedores.registrar("fake", gate=lambda s, b, c: GateResult(True, "modificar_filas" if c.etapa == "reply" else "nueva_solicitud", 0.9))
    proveedores.redactor()
    proveedores.usar(gate="fake")
    fx = fixtures_for("danone")
    harness.deliver(inbound("danone", fx.correos["inbound"], "msg-danone-in", "conv-danone-001"),
                    [fx.xlsx("ampliacion_servicios.xlsx")])
    fh = fixtures_for("holanda")
    harness.deliver(inbound("holanda", fh.correos["init"], "msg-holanda-init", "conv-holanda-001"),
                    [fh.xlsx("Casos REPARE 02032026.xlsx")])
    assert [(d.proveedor_gate, d.tipo_evento) for d in vistas] == [
        ("fake", "modificar_filas"), ("fake", "nueva_solicitud"),
    ]
    assert not hasattr(__import__("classifier"), "ultima_decision")


def test_gate_en_parser_init_cubre_danone_y_penafiel():
    assert service.GATE_EN_PARSER_INIT == {"danone", "penafiel", "test_danone", "test_penafiel"}
    # Los clientes de la Fase 4 (sin gate en su parser) se suman a este set.
    assert {
        "holanda", "heineken", "test_holanda", "test_heineken",
    } <= set(service.PARSERS_INIT) - service.GATE_EN_PARSER_INIT

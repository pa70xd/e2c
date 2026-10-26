"""Golden tests de KOF: los 3 tipos de correo observados (reporte por falla,
bitácora, respuesta de REPARE con OS), el texto plano de proyectos
especiales, la ampliación en el hilo y los comandos bot.*.

Regenerar: ``pytest tests/unit_kof/test_golden_kof.py --update-golden``.
"""

import json
from pathlib import Path

import pytest

from tests.support.scenarios import GLOBAL_ROWS
from tests.unit_kof.conftest import bot_command, inbound, outbound

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "kof"
CORREOS = json.loads((FIXTURES / "correos.json").read_text(encoding="utf-8"))
CONV = "conv-kof-001"


def xlsx(nombre):
    return nombre, (FIXTURES / nombre).read_bytes()


@pytest.mark.golden
def test_reporte_falla_con_hojas_ocultas(kof, golden):
    msg = inbound(CORREOS["init_falla"], "msg-kof-falla", "conv-kof-falla")
    assert kof.deliver(msg, [xlsx("reporte_falla.xlsx")]) == "recibido"
    coolers = kof.repo.calls_to("send_email_coolers")
    # 4 buenas en la visible + 12 en las ocultas; la sin detallista se rechaza.
    assert len(coolers) == 16
    tipos = [c["params"]["parametros"]["tipo_servicio"] for c in coolers]
    assert tipos.count("VENTA DE MATERIAL") == 1
    assert tipos.count("SERVICIO DE DISTRIBUIDOR") == 15
    golden.check("kof_reporte_falla_correo_nuevo", kof.snapshot())


@pytest.mark.golden
def test_bitacora_desdobla_cambio_de_equipo(kof, golden):
    msg = inbound(CORREOS["init_bitacora"], "msg-kof-bitacora", CONV)
    assert kof.deliver(msg, [xlsx("bitacora.xlsx")]) == "recibido"
    coolers = [c["params"]["parametros"] for c in kof.repo.calls_to("send_email_coolers")]
    assert len(coolers) == 9
    assert [c["tipo_servicio"] for c in coolers].count("RETIRO") == 3
    assert {c["folio"] for c in coolers} == {f"80{n:04d}" for n in range(1, 7)}
    golden.check("kof_bitacora_correo_nuevo", kof.snapshot())


@pytest.mark.golden
def test_texto_plano_proyecto_especial(kof, golden):
    msg = inbound(CORREOS["init_texto"], "msg-kof-texto", "conv-kof-texto")
    msg.has_attachments = False
    assert kof.deliver(msg) == "recibido"
    (cooler,) = [c["params"]["parametros"] for c in kof.repo.calls_to("send_email_coolers")]
    assert cooler["tipo_servicio"] == "PROYECTO ESPECIAL"
    assert cooler["serie_fabricante"] is None
    golden.check("kof_texto_plano_proyecto_especial", kof.snapshot())


@pytest.mark.golden
def test_hilo_inbound_agrega_filas(kof, golden):
    kof.repo.set("get_cooler_rows", [{"row_number": n, "status": "PENDING"} for n in range(1, 10)])
    msg = inbound(CORREOS["inbound"], "msg-kof-in", CONV)
    kof.deliver(msg, [xlsx("bitacora.xlsx")])
    filas = [c["params"]["parametros"]["row_number"] for c in kof.repo.calls_to("send_email_coolers")]
    assert filas == list(range(10, 19))
    golden.check("kof_hilo_inbound_con_excel", kof.snapshot())


@pytest.mark.golden
@pytest.mark.parametrize("estado, nombre", [("IN_PROGRESS", "en_proceso"), ("COMPLETED", "completa")])
def test_hilo_outbound_concilia_por_os(kof, golden, estado, nombre):
    kof.repo.set("get_email_request_status", estado)
    msg = outbound(CORREOS["outbound"], f"msg-kof-out-{nombre}", CONV)
    kof.deliver(msg, [xlsx("respuesta_bitacora.xlsx")])
    (llamada,) = kof.repo.calls_to("update_cooler")
    filas = llamada["params"]["df"]["__dataframe__"]["rows"]
    assert len(filas) == 9
    assert sorted(f[3] for f in filas).count("ACCEPTED") == 8
    golden.check(f"kof_hilo_outbound_os_{nombre}", kof.snapshot())


@pytest.mark.golden
@pytest.mark.parametrize("comando", ["ayuda", "estatus", "cancelar", "finalizar", "global"])
def test_hilo_comando_bot(kof, golden, comando):
    if comando == "global":
        kof.repo.set("get_email_request_global", GLOBAL_ROWS)
    msg = bot_command(CORREOS["outbound"]["subject"], CORREOS["comandos"][comando], f"msg-kof-bot-{comando}", CONV)
    kof.deliver(msg)
    assert len(kof.replies) == 1
    golden.check(f"kof_hilo_bot_{comando}", kof.snapshot())


def _xlsx_en_memoria(filas):
    from io import BytesIO

    from openpyxl import Workbook

    wb = Workbook()
    for fila in filas:
        wb.active.append(fila)
    salida = BytesIO()
    wb.save(salida)
    return salida.getvalue()


def test_sin_filas_validas_no_crea_solicitud(kof):
    contenido = _xlsx_en_memoria([["MODELO", "No SERIE", "FALLA", "ID DETALLISTA"], ["VR-1", None, "NO ENFRIA", "D1"]])
    msg = inbound(CORREOS["init_falla"], "msg-kof-rechazadas", "conv-kof-rechazadas")
    kof.deliver(msg, [("reporte.xlsx", contenido)])
    assert "save_email_log_init" not in kof.repo.names()
    (reply,) = kof.replies
    assert "REQUEST REJECTED" in reply["body"]


def test_excel_sin_encabezado_kof_responde_formato_desconocido(kof):
    msg = inbound(CORREOS["init_falla"], "msg-kof-desconocido", "conv-kof-desconocido")
    kof.deliver(msg, [("otro.xlsx", _xlsx_en_memoria([["A", "B"], ["1", "2"]]))])
    assert "save_email_log_init" not in kof.repo.names()
    assert "formato desconocido" in kof.replies[0]["body"]


def test_correo_sin_excel_ni_texto_kof_se_ignora(kof):
    msg = inbound(CORREOS["init_bitacora"], "msg-kof-nada", "conv-kof-nada")
    msg.has_attachments = False
    kof.deliver(msg)
    assert not kof.replies

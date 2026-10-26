"""Nombre, teléfono, correo y dirección vienen en el cuerpo y nunca se
loguean (ni siquiera en los avisos de error)."""

import pytest

from tests.fixtures.oxxo import build_oxxo
from tests.unit_oxxo.conftest import MAILBOX_GARANTIAS, MAILBOX_MANTENIMIENTO

PII = [
    "Persona Ejemplo", "Calle Ficticia", "Colonia Ejemplo", "persona.dos@example.com",
    "5555010002", "55 5501 0002", "50EJE", "TIENDA EJEMPLO",
]


def _sin_pii(texto):
    for dato in PII:
        assert dato not in texto, f"PII en el log: {dato!r}"


@pytest.mark.parametrize("escenario", [
    "mantenimiento", "mantenimiento_sin_ticket", "seguimiento_nuevo", "seguimiento_escalacion",
    "seguimiento_sin_folio", "excel", "excel_roto",
])
def test_los_logs_no_llevan_pii(oxxo, capsys, escenario):
    oxxo.encender()
    adjuntos = None
    con_adjunto = False
    if escenario.startswith("mantenimiento"):
        msg = oxxo.correo(MAILBOX_MANTENIMIENTO, escenario, "msg-pii")
    elif escenario == "seguimiento_sin_folio":
        msg = oxxo.correo(MAILBOX_GARANTIAS, "seguimiento_sin_folio", "msg-pii")
    elif escenario.startswith("seguimiento"):
        if escenario.endswith("escalacion"):
            oxxo.h.repo.set("get_by_folio", {
                "request_code": "REPARE_000042", "row_number": 1, "status": "ACCEPTED", "cliente": "OXXO_GARANTIAS",
            })
        msg = oxxo.correo(MAILBOX_GARANTIAS, "seguimiento", "msg-pii")
    else:
        con_adjunto = True
        adjuntos = (
            [oxxo.xlsm(build_oxxo.EXCEL_INIT)] if escenario == "excel" else [("roto.xlsm", b"x")]
        )
        msg = oxxo.correo(MAILBOX_GARANTIAS, "excel_init", "msg-pii", con_adjunto=con_adjunto)

    oxxo.h.deliver(msg, adjuntos)
    salida = capsys.readouterr()
    _sin_pii(salida.out + salida.err)


def test_error_al_marcar_escalacion_no_loguea_el_mensaje(oxxo, capsys):
    oxxo.encender()
    oxxo.h.repo.set("get_by_folio", {
        "request_code": "REPARE_000042", "row_number": 1, "status": "PENDING", "cliente": "OXXO_GARANTIAS",
    })
    oxxo.h.repo.fail("marcar_escalacion", RuntimeError("falló con Persona Ejemplo Dos"))
    oxxo.h.deliver(oxxo.correo(MAILBOX_GARANTIAS, "seguimiento", "msg-pii-err"))
    salida = capsys.readouterr()
    _sin_pii(salida.out + salida.err)
    assert len(oxxo.h.replies) == 1  # el aviso a REPARE sale aunque no se pudo marcar

"""Integración con el flujo de reply y aviso a REPARE."""

from __future__ import annotations

from classifier import registry
from classifier.contracts import (
    AGREGAR_FILAS,
    CANCELAR_FILAS,
    CANCELAR_SOLICITUD,
    MODIFICAR_FILAS,
    PROVEEDOR_REGEX,
    Decision,
    ThreadCtx,
)
from config.config_general.messages import MENSAJES_REPARE
from review.aplicador import Resultado, aplicar

TIPOS_CON_CAMBIOS = frozenset({AGREGAR_FILAS, MODIFICAR_FILAS, CANCELAR_FILAS, CANCELAR_SOLICITUD})

msj = MENSAJES_REPARE()


def debe_atender(decision: Decision, ctx: ThreadCtx, email) -> bool:
    """El mensaje lo atiende ``review`` y no el parser.

    Solo con ``CLASSIFIER_EXTRACT`` distinto de ``regex``, en un inbound sin
    adjuntos (con Excel manda el Excel, como hoy), con solicitud resuelta y
    con filas que aplicar o revisar."""
    if registry.nombre_extract() == PROVEEDOR_REGEX:
        return False
    if decision is None or ctx is None:
        return False
    if ctx.direccion != "inbound" or not ctx.request_code:
        return False
    if getattr(email, "has_attachments", False):
        return False
    if decision.tipo_evento not in TIPOS_CON_CAMBIOS:
        return False
    if decision.tipo_evento == CANCELAR_SOLICITUD:
        return ctx.filas is not None
    return bool(decision.filas_aplicables or decision.filas_revision)


def _filas_mensaje(filas):
    return [
        {
            "row_number": f.row_number,
            "serie": f.serie,
            "accion": f.accion,
            "motivo": getattr(f, "motivo", None),
        }
        for f in filas
    ]


def _log(resultado: Resultado, ctx: ThreadCtx) -> None:
    # Sin PII: solo códigos, contadores y row_number.
    print(
        f"[REVIEW] cliente={ctx.customer} request_code={resultado.request_code} "
        f"aplicadas={[f.row_number for f in resultado.aplicadas]} "
        f"revision={[(f.row_number, f.accion, f.motivo) for f in resultado.revision]} "
        f"sin_cambios={len(resultado.sin_cambios)} errores={list(resultado.errores)}"
    )


async def atender(decision: Decision, ctx: ThreadCtx, repo, enviar) -> dict:
    """Aplica, manda a REPARE la lista de filas en revisión (``enviar`` es
    ``async fn(mensaje)``, la misma respuesta en el hilo que usan los
    parsers) y devuelve ``{"mensaje": ...}`` con la respuesta del hilo."""
    resultado = aplicar(decision, ctx, repo)
    _log(resultado, ctx)

    revision = _filas_mensaje(resultado.revision)
    if revision:
        try:
            await enviar(msj.msj_revision_repare(resultado.request_code, revision))
        except Exception as e:
            # La respuesta del hilo también lista las filas en revisión.
            print(f"[REVIEW][ERROR] aviso a REPARE no enviado: {type(e).__name__}")

    mensaje = msj.msj_cambios_hilo(
        resultado.request_code,
        _filas_mensaje(resultado.aplicadas),
        revision,
        _filas_mensaje(resultado.sin_cambios),
    )
    return {"mensaje": mensaje, "resultado": resultado}

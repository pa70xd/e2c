"""Cargador del contexto del hilo para el clasificador."""

from __future__ import annotations

from dataclasses import replace

from classifier.contracts import ETAPA_REPLY, FilaGuardada, ThreadCtx


def _texto(valor):
    return None if valor is None else str(valor)


def filas_guardadas(rows) -> tuple[FilaGuardada, ...]:
    return tuple(
        FilaGuardada(
            row_number=int(r["row_number"]),
            status=r["status"],
            serie_fabricante=_texto(r.get("serie_fabricante")),
            serie_dnn_bnf=_texto(r.get("serie_dnn_bnf")),
        )
        for r in rows or ()
        if r.get("row_number") is not None
    )


def cargador(repo):
    """``fn(email, ctx) -> ThreadCtx`` para ``registrar_cargador_contexto``.

    Solo en etapa ``reply``. La solicitud se resuelve por hilo
    (``email_reply_validate``) si el contexto no la trae. Sin solicitud, el
    contexto queda igual (``filas=None``: "no se cargaron")."""

    def cargar(email, ctx: ThreadCtx) -> ThreadCtx:
        if ctx.etapa != ETAPA_REPLY:
            return ctx
        request_code = ctx.request_code
        if not request_code:
            vinculo = repo.email_reply_validate(
                getattr(email, "conversation_id", None),
                getattr(email, "subject", None),
            )
            request_code = (vinculo or {}).get("request_code")
        if not request_code:
            return ctx
        filas = filas_guardadas(repo.get_cooler_rows(request_code))
        return replace(ctx, request_code=request_code, filas=filas)

    return cargar

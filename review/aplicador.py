"""Aplica una ``Decision`` con filas sobre ``cooler_request``.

Solo se escriben filas PENDING, con UPDATE por fila filtrado por
``request_code + row_number + status = 'PENDING'``: si la fila cambió de
estado entre la carga del contexto y el UPDATE, no se toca y va a revisión.

Decisiones de la orquestadora (2026-10-25):

* Un alta desde texto (sin Excel) no se inserta: sin distribuidora ni
  geocodificación rompe las sábanas y Tableau. Va a revisión con
  ``ALTA_SIN_EXCEL``.
* Cancelar una fila ya CANCELLED es idempotente: "sin cambios", sin aviso a
  REPARE.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from classifier.contracts import (
    ACCEPTED,
    AGREGAR,
    CANCELAR,
    CANCELAR_SOLICITUD,
    CANCELLED,
    COMENTARIO_REVISION,
    MODIFICAR,
    PENDING,
    Decision,
    RowExtraida,
    ThreadCtx,
)

# Motivos propios (además de "fila_accepted" y "estado_no_pending" del
# clasificador). Códigos sin PII.
FILA_INEXISTENTE = "fila_inexistente"
ESTADO_CAMBIO = "estado_cambio"
ALTA_SIN_EXCEL = "alta sin Excel; requiere datos completos"
ERROR_REPOSITORIO = "error_repositorio"
YA_CANCELADA = "ya_cancelada"

CAMPOS_CAMBIO = ("folio", "serie_fabricante", "serie_dnn_bnf", "modelo", "tipo_servicio", "direccion")


@dataclass(frozen=True)
class FilaAplicada:
    row_number: int
    accion: str
    serie: Optional[str] = None


@dataclass(frozen=True)
class FilaEnRevision:
    row_number: Optional[int]
    accion: str
    status: Optional[str]
    motivo: str
    serie: Optional[str] = None
    comentario: str = COMENTARIO_REVISION


@dataclass(frozen=True)
class Resultado:
    request_code: Optional[str]
    aplicadas: tuple[FilaAplicada, ...] = ()
    revision: tuple[FilaEnRevision, ...] = ()
    # Pedidos que no cambian nada (p. ej. cancelar una fila ya cancelada).
    sin_cambios: tuple[FilaEnRevision, ...] = ()
    solicitud_cancelada: bool = False
    errores: tuple[str, ...] = field(default_factory=tuple)

    @property
    def requiere_revision(self) -> bool:
        return bool(self.revision)


def _serie(*valores) -> Optional[str]:
    for v in valores:
        if v is not None and str(v).strip():
            return str(v).strip()
    return None


def _serie_guardada(ctx: ThreadCtx, row_number) -> Optional[str]:
    fila = ctx.fila(row_number) if row_number is not None else None
    return _serie(fila.serie_fabricante, fila.serie_dnn_bnf) if fila else None


def aplicar(decision: Decision, ctx: ThreadCtx, repo) -> Resultado:
    """Aplica las filas PENDING de ``decision``. Todo lo demás va a revisión.

    ``repo`` es un ``DB_POSTGRE`` (o un doble con los mismos métodos)."""
    request_code = ctx.request_code
    aplicadas: list[FilaAplicada] = []
    revision: list[FilaEnRevision] = []
    sin_cambios: list[FilaEnRevision] = []
    errores: list[str] = []

    def a_revision(row_number, accion, status, motivo, serie=None):
        revision.append(FilaEnRevision(
            row_number=row_number,
            accion=accion,
            status=status,
            motivo=motivo,
            serie=serie or _serie_guardada(ctx, row_number),
        ))

    def escribir(fn, row_number, accion, *args):
        try:
            tocadas = fn(request_code, row_number, *args)
        except Exception as e:
            errores.append(f"{accion}:{row_number}:{type(e).__name__}")
            a_revision(row_number, accion, PENDING, ERROR_REPOSITORIO)
            return
        if tocadas:
            aplicadas.append(FilaAplicada(row_number, accion, _serie_guardada(ctx, row_number)))
        else:
            # Ya no es PENDING (o desapareció) desde que se cargó el contexto.
            a_revision(row_number, accion, None, ESTADO_CAMBIO)

    for fr in decision.filas_revision:
        if fr.accion == CANCELAR and fr.status == CANCELLED:
            sin_cambios.append(FilaEnRevision(
                fr.row_number, CANCELAR, CANCELLED, YA_CANCELADA, _serie_guardada(ctx, fr.row_number)
            ))
            continue
        motivo = FILA_INEXISTENTE if fr.status is None else fr.motivo
        a_revision(fr.row_number, fr.accion, fr.status, motivo)

    if not request_code:
        # Sin solicitud no hay nada que aplicar: todo a revisión.
        for row in decision.filas_aplicables:
            a_revision(row.row_number, row.accion, None, FILA_INEXISTENTE,
                       _serie(row.serie_fabricante, row.serie_dnn_bnf))
        return Resultado(None, (), tuple(revision), (), False, tuple(errores))

    for row in decision.filas_aplicables:
        if row.accion == AGREGAR:
            a_revision(None, AGREGAR, None, ALTA_SIN_EXCEL,
                       _serie(row.serie_fabricante, row.serie_dnn_bnf))
            continue

        fila = ctx.fila(row.row_number)
        if fila is None:
            a_revision(row.row_number, row.accion, None, FILA_INEXISTENTE)
            continue
        if row.accion == CANCELAR and fila.status == CANCELLED:
            sin_cambios.append(FilaEnRevision(
                row.row_number, CANCELAR, CANCELLED, YA_CANCELADA, _serie_guardada(ctx, row.row_number)
            ))
            continue
        if fila.status != PENDING:
            # El clasificador ya debió mandarla a revisión; por si acaso.
            motivo = "fila_accepted" if fila.status == ACCEPTED else "estado_no_pending"
            a_revision(row.row_number, row.accion, fila.status, motivo)
            continue

        if row.accion == MODIFICAR:
            cambios = {c: getattr(row, c) for c in CAMPOS_CAMBIO}
            escribir(repo.update_pending_cooler_row, row.row_number, MODIFICAR, cambios)
        elif row.accion == CANCELAR:
            escribir(repo.cancel_pending_cooler_row, row.row_number, CANCELAR)

    solicitud_cancelada = False
    if decision.tipo_evento == CANCELAR_SOLICITUD and not decision.rows and ctx.filas is not None:
        for fila in ctx.filas:
            if fila.status == PENDING:
                escribir(repo.cancel_pending_cooler_row, fila.row_number, CANCELAR)

    if aplicadas or (decision.tipo_evento == CANCELAR_SOLICITUD and not revision):
        try:
            repo.update_email_request(request_code)
        except Exception as e:
            errores.append(f"update_email_request:{type(e).__name__}")

    if decision.tipo_evento == CANCELAR_SOLICITUD and not revision and ctx.filas is not None:
        # Con filas en revisión la solicitud sigue abierta: decide REPARE.
        try:
            solicitud_cancelada = bool(repo.cancel_email_request(request_code))
        except Exception as e:
            errores.append(f"cancel_email_request:{type(e).__name__}")

    return Resultado(
        request_code=request_code,
        aplicadas=tuple(aplicadas),
        revision=tuple(revision),
        sin_cambios=tuple(sin_cambios),
        solicitud_cancelada=solicitud_cancelada,
        errores=tuple(errores),
    )

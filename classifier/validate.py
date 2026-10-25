"""Validación determinista de lo que devuelve un proveedor.

Cada función regresa una lista de errores. Un error es un código corto sin
PII: nombre de campo, índice de fila o valor de un enum, nunca texto del
correo ni series. Lista vacía = válido.

Además, ``separar_revision`` aplica las reglas de negocio de filas ACCEPTED
(ver ``classifier.contracts``).
"""

from __future__ import annotations

from classifier.contracts import (
    ACCEPTED,
    ACCION_POR_TIPO,
    ACCIONES,
    AGREGAR,
    CAMPOS_FILA,
    CANCELAR,
    CANCELAR_SOLICITUD,
    CANCELLED,
    ETAPA_INIT,
    ETAPA_REPLY,
    ETAPAS,
    NUEVA_SOLICITUD,
    PENDING,
    TIPOS_DE_HILO,
    TIPOS_EVENTO,
    TIPOS_SIN_OS,
    FilaRevision,
    GateResult,
    RowExtraida,
    ThreadCtx,
)

MAX_LARGO_CAMPO = 300
MAX_FILAS = 500


def validar_gate(result, thread_ctx: ThreadCtx, min_confidence: float) -> list[str]:
    if not isinstance(result, GateResult):
        return ["gate:tipo_invalido"]

    errores = []
    if not isinstance(result.es_os, bool):
        errores.append("gate:es_os_no_bool")
    if result.tipo_evento not in TIPOS_EVENTO:
        errores.append("gate:tipo_evento_invalido")
    conf = result.confidence
    if isinstance(conf, bool) or not isinstance(conf, (int, float)) or not 0.0 <= conf <= 1.0:
        errores.append("gate:confidence_fuera_de_rango")
    elif conf < min_confidence:
        errores.append("gate:confianza_baja")
    if errores:
        return errores

    if result.es_os == (result.tipo_evento in TIPOS_SIN_OS):
        errores.append("gate:es_os_incoherente")

    if thread_ctx.etapa not in ETAPAS:
        errores.append("ctx:etapa_invalida")
    elif thread_ctx.etapa == ETAPA_INIT and result.tipo_evento in TIPOS_DE_HILO:
        errores.append("ctx:evento_de_hilo_sin_hilo")
    elif thread_ctx.etapa == ETAPA_REPLY and result.tipo_evento == NUEVA_SOLICITUD:
        errores.append("ctx:nueva_solicitud_en_hilo")

    return errores


def _texto_ok(valor) -> bool:
    return valor is None or (isinstance(valor, str) and len(valor) <= MAX_LARGO_CAMPO)


def validar_rows(rows, gate: GateResult, thread_ctx: ThreadCtx) -> list[str]:
    if not isinstance(rows, (list, tuple)):
        return ["rows:tipo_invalido"]
    if len(rows) > MAX_FILAS:
        return ["rows:demasiadas"]
    if rows and not gate.es_os:
        return ["rows:sin_os"]

    accion_esperada = ACCION_POR_TIPO.get(gate.tipo_evento)
    if rows and accion_esperada is None:
        # cancelar_solicitud, estatus: el evento no lleva filas.
        return ["rows:evento_sin_filas"]

    errores = []
    vistos = set()
    for i, row in enumerate(rows):
        if not isinstance(row, RowExtraida):
            errores.append(f"rows[{i}]:tipo_invalido")
            continue
        if row.accion not in ACCIONES:
            errores.append(f"rows[{i}]:accion_invalida")
            continue
        if row.accion != accion_esperada:
            errores.append(f"rows[{i}]:accion_incoherente_con_evento")
        for campo in CAMPOS_FILA:
            if not _texto_ok(getattr(row, campo)):
                errores.append(f"rows[{i}]:{campo}_invalido")

        rn = row.row_number
        if rn is not None and (isinstance(rn, bool) or not isinstance(rn, int) or rn < 1):
            errores.append(f"rows[{i}]:row_number_invalido")
            continue

        if row.accion == AGREGAR:
            if rn is not None:
                errores.append(f"rows[{i}]:agregar_con_row_number")
            continue

        # modificar / cancelar: la fila referida debe existir en el hilo.
        if rn is None:
            errores.append(f"rows[{i}]:row_number_requerido")
        elif thread_ctx.filas is None:
            errores.append(f"rows[{i}]:filas_no_cargadas")
        elif thread_ctx.fila(rn) is None:
            errores.append(f"rows[{i}]:fila_inexistente")
        elif rn in vistos:
            errores.append(f"rows[{i}]:fila_repetida")
        if rn is not None:
            vistos.add(rn)

    return errores


def _revision(row_number, accion, status) -> FilaRevision:
    motivo = "fila_accepted" if status == ACCEPTED else "estado_no_pending"
    return FilaRevision(row_number=row_number, accion=accion, status=status, motivo=motivo)


def separar_revision(rows, gate: GateResult, thread_ctx: ThreadCtx):
    """(aplicables, revision). Modificar o cancelar una fila que no es
    PENDING (en especial ACCEPTED) nunca se aplica: va a revisión.

    ``cancelar_solicitud`` sin filas explícitas manda a revisión las filas no
    PENDING (y no ya canceladas) del hilo, si se cargaron.
    """
    aplicables, revision = [], []

    for row in rows:
        if row.accion == AGREGAR:
            aplicables.append(row)
            continue
        fila = thread_ctx.fila(row.row_number)
        if fila is not None and fila.status == PENDING:
            aplicables.append(row)
        else:
            revision.append(_revision(row.row_number, row.accion, fila.status if fila else None))

    if gate.tipo_evento == CANCELAR_SOLICITUD and not rows:
        for fila in thread_ctx.filas or ():
            if fila.status not in (PENDING, CANCELLED):
                revision.append(_revision(fila.row_number, CANCELAR, fila.status))

    return tuple(aplicables), tuple(revision)

"""Capa de lectura del cuerpo del correo con proveedores intercambiables.

Contratos y reglas en ``classifier/contracts.py``. Con el proveedor por
defecto (``regex``) el resultado es idéntico al comportamiento anterior y no
se escribe ningún log adicional.

Uso:

* ``gate_proposito(customer, subject, body)``: decisión de ``init`` (desde
  ``analizar_proposito`` de Danone y Penafiel).
* ``decidir_correo(email, customer, etapa, direccion)``: decisión desde
  ``src/service.py`` (mensajes de hilo y ``init`` de Holanda y Heineken).
* ``debe_continuar(decision, thread_ctx)``: si el correo sigue al parser.
* ``ultima_decision()``: la última ``Decision`` del contexto actual (la misma
  tarea async de ``processMail``; para el
  canal de revisión: ``Decision.filas_revision``).
"""

from __future__ import annotations

from contextvars import ContextVar

from classifier import registry, validate
from classifier.contracts import (
    ETAPA_INIT,
    PROVEEDOR_REGEX,
    Decision,
    ProveedorNoDisponible,
    ThreadCtx,
)
from classifier.providers import regex as regex_provider

_ULTIMA: ContextVar = ContextVar("classifier_ultima_decision", default=None)

# Direcciones internas de REPARE: los comandos bot.* son deterministas y el
# gate no los bloquea.
DIRECCIONES_BOT = frozenset({"reply_to_bot", "bot"})

# Cargador opcional del contexto del hilo: fn(email, ctx_base) -> ThreadCtx.
# Solo se usa con un proveedor externo (con regex no se consulta nada).
_cargador_contexto = None


def registrar_cargador_contexto(fn) -> None:
    global _cargador_contexto
    _cargador_contexto = fn


def ultima_decision() -> Decision | None:
    return _ULTIMA.get()


def _codigo_error(e: BaseException) -> str:
    # El mensaje de un proveedor externo podría traer texto del correo: solo
    # se loguea la clase, salvo los errores propios del registro.
    if isinstance(e, (ProveedorNoDisponible, _RedaccionFallida)):
        return str(e)
    return type(e).__name__


def _log(decision: Decision, ctx: ThreadCtx) -> None:
    print(
        f"[CLASSIFIER] etapa={ctx.etapa} cliente={ctx.customer} "
        f"direccion={ctx.direccion} gate={decision.proveedor_gate} "
        f"tipo={decision.tipo_evento} es_os={decision.es_os} "
        f"confidence={decision.gate.confidence:.2f} extract={decision.proveedor_extract} "
        f"filas={len(decision.rows)} revision={len(decision.filas_revision)} "
        f"fallbacks={list(decision.fallbacks)}"
    )


def decidir(subject, body, thread_ctx: ThreadCtx) -> Decision:
    """gate + extract + validación + reglas de revisión.

    Un proveedor externo que falla o no valida cae a ``regex``. Las
    excepciones de ``regex`` se propagan igual que antes.
    """
    nombre_gate = registry.nombre_gate()
    nombre_extract = registry.nombre_extract()
    fallbacks: list[str] = []
    redactado: tuple | None = None

    def texto_redactado():
        nonlocal redactado
        if redactado is None:
            redact = registry.get_redactor()
            try:
                redactado = (
                    redact(subject) if subject else subject,
                    redact(body or ""),
                )
            except NotImplementedError:
                raise _RedaccionFallida("redaccion_no_disponible") from None
            except Exception:
                raise _RedaccionFallida("redaccion_error") from None
        return redactado

    gate = None
    proveedor_gate = PROVEEDOR_REGEX
    if nombre_gate != PROVEEDOR_REGEX:
        try:
            proveedor = registry.cargar(nombre_gate)
            s, b = texto_redactado()
            resultado = proveedor.gate(s, b, thread_ctx)
            errores = validate.validar_gate(resultado, thread_ctx, registry.min_confidence())
            if errores:
                fallbacks.append(f"gate:{nombre_gate}:{','.join(errores)}")
            else:
                gate, proveedor_gate = resultado, nombre_gate
        except Exception as e:
            fallbacks.append(f"gate:{nombre_gate}:{_codigo_error(e)}")
    if gate is None:
        gate = regex_provider.gate(subject, body, thread_ctx)

    rows = None
    proveedor_extract = PROVEEDOR_REGEX
    if gate.es_os and nombre_extract != PROVEEDOR_REGEX:
        try:
            proveedor = registry.cargar(nombre_extract)
            _, b = texto_redactado()
            salida = proveedor.extract(b, thread_ctx)
            salida = list(salida) if isinstance(salida, (list, tuple)) else salida
            errores = validate.validar_rows(salida, gate, thread_ctx)
            if errores:
                fallbacks.append(f"extract:{nombre_extract}:{','.join(errores[:10])}")
            else:
                rows, proveedor_extract = tuple(salida), nombre_extract
        except Exception as e:
            fallbacks.append(f"extract:{nombre_extract}:{_codigo_error(e)}")
    if rows is None:
        rows = tuple(regex_provider.extract(body, thread_ctx)) if gate.es_os else ()

    aplicables, revision = validate.separar_revision(rows, gate, thread_ctx)
    decision = Decision(
        gate=gate,
        proveedor_gate=proveedor_gate,
        proveedor_extract=proveedor_extract,
        rows=rows,
        filas_aplicables=aplicables,
        filas_revision=revision,
        fallbacks=tuple(fallbacks),
    )
    _ULTIMA.set(decision)

    if nombre_gate != PROVEEDOR_REGEX or nombre_extract != PROVEEDOR_REGEX:
        _log(decision, thread_ctx)
    return decision


class _RedaccionFallida(Exception):
    def __str__(self):
        return self.args[0]


def gate_proposito(customer, subject, body) -> bool:
    """Decisión de ``init``: ¿el correo pide una OS?"""
    ctx = ThreadCtx(etapa=ETAPA_INIT, customer=customer)
    return decidir(subject, body, ctx).es_os


def _usa_externo() -> bool:
    return PROVEEDOR_REGEX != registry.nombre_gate() or PROVEEDOR_REGEX != registry.nombre_extract()


def decidir_correo(email, customer, etapa, direccion=None) -> tuple[Decision, ThreadCtx]:
    """Decide sobre un ``Message`` de Graph. El contexto del hilo solo se
    carga (con el cargador registrado) si hay un proveedor externo."""
    ctx = ThreadCtx(etapa=etapa, customer=customer, direccion=direccion)
    if _cargador_contexto is not None and _usa_externo():
        try:
            ctx = _cargador_contexto(email, ctx)
        except Exception as e:
            print(f"[CLASSIFIER][ERROR] contexto del hilo no cargado: {type(e).__name__}")

    body = getattr(getattr(email, "unique_body", None), "content", None)
    return decidir(getattr(email, "subject", None), body, ctx), ctx


def debe_continuar(decision: Decision, thread_ctx: ThreadCtx) -> bool:
    """El correo sigue al parser si es OS. Los comandos internos de REPARE
    (``reply_to_bot``/``bot``) siempre siguen."""
    return decision.es_os or thread_ctx.direccion in DIRECCIONES_BOT

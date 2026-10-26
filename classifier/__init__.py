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

Duda del modelo (usuario, 2026-10-26): en etapa ``reply``, si el gate externo
cae SOLO por confianza baja (``gate:confianza_baja``), la decisión de regex no
se usa para aplicar cambios por texto: la ``Decision`` sale sin filas y con
``motivo_revision = "clasificación dudosa"`` (``review`` avisa a REPARE). El
gate sigue siendo el de regex para que el parser (Excel, comandos bot,
outbound) corra exactamente igual que antes. En ``init`` la duda cae a regex
como siempre: ahí decide el Excel del parser, el texto no se aplica. Las demás
caídas (timeout, error de API, sin key, PII sin redactar, salida inválida)
siguen cayendo a regex sin aviso. ``extract`` no reporta confianza en el
contrato; si algún proveedor llegara a caer por ``confianza_baja`` en el
extract, aplica la misma regla.

La ``Decision`` viaja como valor de retorno; no hay estado global (varios
correos se procesan en paralelo). ``src/service.py`` la deja en el parser del
correo como ``parser.classifier_decision`` (``Decision.filas_revision`` para
el canal de revisión).
"""

from __future__ import annotations

from classifier import registry, validate
from classifier.contracts import (
    ETAPA_INIT,
    ETAPA_REPLY,
    MOTIVO_CLASIFICACION_DUDOSA,
    PROVEEDOR_REGEX,
    Decision,
    ProveedorNoDisponible,
    ThreadCtx,
)
from classifier.providers import regex as regex_provider

# Direcciones internas de REPARE: los comandos bot.* son deterministas y el
# gate no los bloquea.
DIRECCIONES_BOT = frozenset({"reply_to_bot", "bot"})

# REPARE -> cliente (``outbound`` en ``EMAIL_TYPE.detect_direccion``): la
# respuesta con el Excel de OS generadas es lo que cierra las filas. Un
# clasificador externo la vería como ``no_os``; nunca se bloquea.
DIRECCIONES_REPARE = DIRECCIONES_BOT | {"outbound"}

# Cargador opcional del contexto del hilo: fn(email, ctx_base) -> ThreadCtx.
# Solo se usa con un proveedor externo (con regex no se consulta nada).
_cargador_contexto = None


def registrar_cargador_contexto(fn) -> None:
    global _cargador_contexto
    _cargador_contexto = fn


def _codigo_error(e: BaseException) -> str:
    # El mensaje de un proveedor externo podría traer texto del correo: solo
    # se loguea la clase, salvo los errores propios del registro.
    if isinstance(e, (ProveedorNoDisponible, _RedaccionFallida)):
        return str(e)
    return type(e).__name__


def _es_duda(errores) -> bool:
    """El proveedor respondió bien pero con confianza baja (y nada más)."""
    return bool(errores) and all(e.endswith(":confianza_baja") for e in errores)


def _log(decision: Decision, ctx: ThreadCtx) -> None:
    print(
        f"[CLASSIFIER] etapa={ctx.etapa} cliente={ctx.customer} "
        f"direccion={ctx.direccion} gate={decision.proveedor_gate} "
        f"tipo={decision.tipo_evento} es_os={decision.es_os} "
        f"confidence={decision.gate.confidence:.2f} extract={decision.proveedor_extract} "
        f"filas={len(decision.rows)} revision={len(decision.filas_revision)} "
        f"fallbacks={list(decision.fallbacks)} motivo_revision={decision.motivo_revision}"
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
    # Duda del modelo en un hilo: revisión humana en lugar de regex.
    duda = False
    puede_dudar = thread_ctx.etapa == ETAPA_REPLY

    def texto_redactado():
        nonlocal redactado
        if redactado is None:
            # Las series ya guardadas no se redactan (parecen teléfonos).
            conservar = thread_ctx.series()
            try:
                redact = registry.get_redactor()
                redactado = (
                    redact(subject, conservar=conservar) if subject else subject,
                    redact(body or "", conservar=conservar),
                )
            except (ImportError, NotImplementedError):
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
                duda = puede_dudar and _es_duda(errores)
            else:
                gate, proveedor_gate = resultado, nombre_gate
        except Exception as e:
            fallbacks.append(f"gate:{nombre_gate}:{_codigo_error(e)}")
    if gate is None:
        gate = regex_provider.gate(subject, body, thread_ctx)

    rows = None
    invalidas: tuple = ()
    proveedor_extract = PROVEEDOR_REGEX
    if gate.es_os and nombre_extract != PROVEEDOR_REGEX and not duda:
        try:
            proveedor = registry.cargar(nombre_extract)
            _, b = texto_redactado()
            salida = proveedor.extract(b, thread_ctx, gate=gate)
            salida = list(salida) if isinstance(salida, (list, tuple)) else salida
            # Las filas inválidas van a revisión; el resto se aplica.
            errores, validas, invalidas = validate.separar_invalidas(salida, gate, thread_ctx)
            if errores:
                fallbacks.append(f"extract:{nombre_extract}:{','.join(errores[:10])}")
                duda = puede_dudar and _es_duda(errores)
            else:
                rows, proveedor_extract = validas, nombre_extract
        except Exception as e:
            fallbacks.append(f"extract:{nombre_extract}:{_codigo_error(e)}")
    if rows is None:
        rows = tuple(regex_provider.extract(body, thread_ctx, gate=gate)) if gate.es_os else ()

    if duda:
        # Nada por texto: ni filas de regex ni las reglas de cancelar_solicitud.
        rows, aplicables, revision = (), (), ()
    else:
        aplicables, revision = validate.separar_revision(rows, gate, thread_ctx)
        revision = invalidas + revision
    decision = Decision(
        gate=gate,
        proveedor_gate=proveedor_gate,
        proveedor_extract=proveedor_extract,
        rows=rows,
        filas_aplicables=aplicables,
        filas_revision=revision,
        fallbacks=tuple(fallbacks),
        motivo_revision=MOTIVO_CLASIFICACION_DUDOSA if duda else None,
    )

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
    """El correo sigue al parser si es OS. Lo que escribe REPARE (comandos
    ``reply_to_bot``/``bot`` y la respuesta ``outbound`` al cliente) siempre
    sigue; solo el inbound del cliente puede detenerse."""
    return decision.es_os or thread_ctx.direccion in DIRECCIONES_REPARE

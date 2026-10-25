"""Proveedor ``regex``: envuelve la lógica actual sin cambiarla.

* ``init`` en Danone y Penafiel: ``analizar_proposito_regex`` (los patrones de
  ``config/customers/*/movimientos_*.py``).
* ``init`` en Holanda y Heineken: hoy el parser no lee el cuerpo (decide por
  asunto y Excel), así que el gate deja pasar y el parser decide igual que
  antes.
* ``reply``: hoy todo mensaje de hilo llega al parser; el cuerpo solo se lee
  para las palabras reservadas ``bot.*`` (misma búsqueda que
  ``parsers.core.correo.detectar_tipo_correo``, sin pedir adjuntos a Graph).
  Sin palabra, el parser actualiza filas con el Excel (upsert): regex no
  distingue agregar de modificar y reporta ``modificar_filas``.
* ``extract``: ``[]``. Las filas salen del Excel.

Recibe el texto original (sin redactar): corre local.
"""

from __future__ import annotations

from config.config_general.palabras_reser import palabras_reservadas

from classifier.contracts import (
    CANCELAR_SOLICITUD,
    ESTATUS,
    ETAPA_INIT,
    MODIFICAR_FILAS,
    NO_OS,
    NUEVA_SOLICITUD,
    PROVEEDOR_REGEX,
    GateResult,
)

NAME = PROVEEDOR_REGEX

# Comando bot.* -> tipo_evento.
_TIPO_POR_COMANDO = {
    "bot.cancelar": CANCELAR_SOLICITUD,
}


def _cliente_base(customer):
    cliente = (customer or "").lower().strip()
    return cliente[len("test_"):] if cliente.startswith("test_") else cliente


def _gate_init(subject, body, thread_ctx):
    cliente = _cliente_base(thread_ctx.customer)

    if cliente == "danone":
        from parsers.danone_parse.utils import DANONE_UTILS
        es_os = DANONE_UTILS.analizar_proposito_regex(body, subject)
    elif cliente == "penafiel":
        from parsers.penafiel_parse.utils import PENAFIEL_UTILS
        # parsers/penafiel.py ya concatena cuerpo + asunto y llama sin asunto.
        texto = body if subject is None else (body or "") + subject
        es_os = PENAFIEL_UTILS.analizar_proposito_regex(texto)
    else:
        return GateResult(True, NUEVA_SOLICITUD, 1.0, "delegado_al_parser")

    return GateResult(
        bool(es_os),
        NUEVA_SOLICITUD if es_os else NO_OS,
        1.0,
        "analizar_proposito",
    )


def comando_bot(body):
    """Primera palabra reservada contenida en el cuerpo, o None."""
    texto = f"{body if body is not None else ''}".lower()
    for palabra in palabras_reservadas:
        palabra = palabra.lower()
        if palabra in texto:
            return palabra
    return None


def _gate_reply(subject, body, thread_ctx):
    palabra = comando_bot(body)
    if palabra is None:
        return GateResult(True, MODIFICAR_FILAS, 1.0, "excel_upsert")
    return GateResult(True, _TIPO_POR_COMANDO.get(palabra, ESTATUS), 1.0, palabra)


def gate(subject, body_redacted, thread_ctx) -> GateResult:
    if thread_ctx.etapa == ETAPA_INIT:
        return _gate_init(subject, body_redacted, thread_ctx)
    return _gate_reply(subject, body_redacted, thread_ctx)


def extract(body_redacted, thread_ctx, gate=None):
    return []

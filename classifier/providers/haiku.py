"""Proveedor ``haiku``: gate y extract con Claude Haiku 5.5.

* Recibe SOLO texto ya redactado. Antes de llamar a la API revisa que no
  quede un correo o teléfono; si queda, no hay llamada y la decisión cae a
  ``regex`` (``ProveedorNoDisponible``).
* Salida estructurada con ``output_config.format`` (JSON schema, enums
  cerrados de ``classifier.contracts``). La validación final es de
  ``classifier.validate``: aquí solo se arman los dataclasses con lo que
  devolvió el modelo.
* Parte fija del prompt (instrucciones + few-shot, ``classifier/prompts``) en
  ``system`` con ``cache_control``; el hilo y el correo van en el mensaje.
* Timeout corto y un solo reintento del SDK. Cualquier fallo lanza una
  excepción que ``classifier.decidir`` ya maneja para caer a ``regex``.
* Logs sin PII: solo operación, tipo_evento, confidence y latencia.

Variable opcional: ``ANTHROPIC_API_KEY``. Sin ella el proveedor no se usa.
"""

from __future__ import annotations

import json
import os
import re
import time
from functools import lru_cache
from pathlib import Path
from typing import Optional

from classifier.contracts import (
    ACCIONES,
    CAMPOS_FILA,
    TIPOS_EVENTO,
    GateResult,
    ProveedorNoDisponible,
    RowExtraida,
    ThreadCtx,
)

NAME = "haiku"

MODEL = "claude-haiku-5-5"
TIMEOUT_S = 8.0
MAX_RETRIES = 1
MAX_TOKENS = 4096
EFFORT = "low"
MAX_DETALLE = 60

_PROMPTS = Path(__file__).resolve().parent.parent / "prompts"

_LOG = "[HAIKU]"


# ------------------------------------------------------------------ errores
class HaikuError(RuntimeError):
    """Fallo del proveedor. La clase es el código (sin PII) que se loguea."""


class HaikuTimeout(HaikuError):
    pass


class HaikuApiError(HaikuError):
    pass


class HaikuRechazo(HaikuError):
    pass


class HaikuSalidaInvalida(HaikuError):
    pass


# ------------------------------------------------------------------ prompts
@lru_cache(maxsize=None)
def _prompt(nombre: str) -> tuple[str, str]:
    """(texto, versión) de ``classifier/prompts/<nombre>.md``."""
    texto = (_PROMPTS / f"{nombre}.md").read_text(encoding="utf-8")
    m = re.match(r"<!--\s*version:\s*(\S+)\s*-->", texto)
    return texto, (m.group(1) if m else "sin_version")


def version_prompt(nombre: str) -> str:
    return _prompt(nombre)[1]


# ------------------------------------------------------------------ PII
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_TELEFONO = re.compile(
    r"(?<!\d)(?:"
    r"\+\d{1,3}[\s.-]?\(?\d{2,3}\)?[\s.-]?\d{3,4}[\s.-]?\d{4}"  # +52 55 1234 5678
    r"|\(?\d{2,3}\)?[\s.-]\d{3,4}[\s.-]\d{4}"                  # 55-1234-5678, (55) 1234 5678
    r"|\d{2}[\s.-]\d{4}[\s.-]\d{4}"
    r")(?!\d)"
    r"|(?:tel|tel[eé]fono|cel|celular|whatsapp|wa)\W{0,3}\d{10}(?!\d)",
    re.IGNORECASE,
)


def _hay_pii(*textos: Optional[str], conservar: tuple = ()) -> bool:
    """Correo o teléfono en el texto. Las series ya guardadas en el hilo
    (``conservar``) no cuentan: ``redact`` las deja pasar a propósito."""
    for t in textos:
        if not t:
            continue
        for serie in sorted(conservar, key=len, reverse=True):
            t = t.replace(serie, " ")
        if _EMAIL.search(t) or _TELEFONO.search(t):
            return True
    return False


# ------------------------------------------------------------------ cliente
_NULO_TEXTO = {"anyOf": [{"type": "string"}, {"type": "null"}]}

_SCHEMA_GATE = {
    "type": "object",
    "properties": {
        "es_os": {"type": "boolean"},
        "tipo_evento": {"type": "string", "enum": list(TIPOS_EVENTO)},
        "confidence": {"type": "number"},
        "detalle": {"type": "string"},
    },
    "required": ["es_os", "tipo_evento", "confidence", "detalle"],
    "additionalProperties": False,
}

_SCHEMA_EXTRACT = {
    "type": "object",
    "properties": {
        "rows": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "accion": {"type": "string", "enum": list(ACCIONES)},
                    **{campo: _NULO_TEXTO for campo in CAMPOS_FILA},
                    "row_number": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
                },
                "required": ["accion", *CAMPOS_FILA, "row_number"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["rows"],
    "additionalProperties": False,
}

_client = None
_client_key = None


def _get_client():
    """Cliente de Anthropic. ``ProveedorNoDisponible`` si no hay API key."""
    global _client, _client_key
    key = (os.getenv("ANTHROPIC_API_KEY") or "").strip()
    if not key:
        print(f"{_LOG} ANTHROPIC_API_KEY no configurada: se usa regex")
        raise ProveedorNoDisponible("haiku_sin_api_key")
    if _client is None or _client_key != key:
        import anthropic

        _client = anthropic.Anthropic(api_key=key, timeout=TIMEOUT_S, max_retries=MAX_RETRIES)
        _client_key = key
    return _client


def _llamar(op: str, schema: dict, contenido: str) -> dict:
    """Una llamada a Haiku. Devuelve el JSON ya decodificado."""
    import anthropic

    cliente = _get_client()
    texto_prompt, _ = _prompt(op)
    t0 = time.monotonic()
    try:
        resp = cliente.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=[{
                "type": "text",
                "text": texto_prompt,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{"role": "user", "content": contenido}],
            output_config={"effort": EFFORT, "format": {"type": "json_schema", "schema": schema}},
        )
    except anthropic.APITimeoutError:
        _log_error(op, "HaikuTimeout", t0)
        raise HaikuTimeout("timeout") from None
    except anthropic.APIError as e:
        _log_error(op, "HaikuApiError", t0, getattr(e, "status_code", None))
        raise HaikuApiError(f"api_{getattr(e, 'status_code', None) or type(e).__name__}") from None

    if resp.stop_reason == "refusal":
        _log_error(op, "HaikuRechazo", t0)
        raise HaikuRechazo("rechazo")
    if resp.stop_reason == "max_tokens":
        _log_error(op, "HaikuSalidaInvalida", t0)
        raise HaikuSalidaInvalida("max_tokens")

    texto = next((b.text for b in resp.content if b.type == "text"), None)
    try:
        datos = json.loads(texto)
    except (TypeError, ValueError):
        _log_error(op, "HaikuSalidaInvalida", t0)
        raise HaikuSalidaInvalida("json_invalido") from None
    if not isinstance(datos, dict):
        _log_error(op, "HaikuSalidaInvalida", t0)
        raise HaikuSalidaInvalida("json_no_objeto")

    uso = getattr(resp, "usage", None)
    datos["__lat_ms"] = int((time.monotonic() - t0) * 1000)
    datos["__cache_read"] = getattr(uso, "cache_read_input_tokens", None)
    return datos


def _log_ok(op: str, datos: dict, **campos) -> None:
    extra = " ".join(f"{k}={v}" for k, v in campos.items())
    print(
        f"{_LOG} op={op} prompt={version_prompt(op)} {extra} "
        f"latencia_ms={datos['__lat_ms']} cache_read={datos['__cache_read']}"
    )


def _log_error(op: str, codigo: str, t0: float, status=None) -> None:
    print(
        f"{_LOG} op={op} error={codigo} status={status} "
        f"latencia_ms={int((time.monotonic() - t0) * 1000)}"
    )


# ------------------------------------------------------------------ contexto
def _render_ctx(ctx: ThreadCtx) -> str:
    lineas = [f"etapa: {ctx.etapa}"]
    if ctx.customer:
        lineas.append(f"cliente: {ctx.customer}")
    if ctx.direccion:
        lineas.append(f"direccion: {ctx.direccion}")
    if ctx.decisiones:
        previas = ", ".join(f"{d.tipo_evento}(es_os={d.es_os})" for d in ctx.decisiones)
        lineas.append(f"decisiones previas del hilo: {previas}")
    if ctx.filas is None and ctx.etapa == "init":
        lineas.append("filas guardadas: ninguna")
    elif ctx.filas is None:
        lineas.append("filas guardadas: no se cargaron")
    elif not ctx.filas:
        lineas.append("filas guardadas: ninguna")
    else:
        lineas.append("filas guardadas:")
        for f in ctx.filas:
            series = ", ".join(
                s for s in (f.serie_fabricante, f.serie_dnn_bnf) if s
            ) or "sin series"
            lineas.append(f"  fila {f.row_number} ({f.status}): {series}")
    return "\n".join(lineas)


def _mensaje(ctx: ThreadCtx, body: str, subject: Optional[str] = None, gate: Optional[GateResult] = None) -> str:
    partes = [f"<contexto>\n{_render_ctx(ctx)}\n</contexto>"]
    if gate is not None:
        partes.append(f"<tipo_evento>{gate.tipo_evento}</tipo_evento>")
    if subject:
        partes.append(f"<asunto>\n{subject}\n</asunto>")
    partes.append(f"<correo>\n{body}\n</correo>")
    return "\n".join(partes)


def _exigir_redactado(op: str, ctx: ThreadCtx, *textos: Optional[str]) -> None:
    if _hay_pii(*textos, conservar=ctx.series()):
        print(f"{_LOG} op={op} texto con correo o teléfono sin redactar: no se llama a la API")
        raise ProveedorNoDisponible("haiku_pii_sin_redactar")


# ------------------------------------------------------------------ API pública
def gate(subject: Optional[str], body_redacted: str, thread_ctx: ThreadCtx) -> GateResult:
    _exigir_redactado("gate", thread_ctx, subject, body_redacted)
    datos = _llamar("gate", _SCHEMA_GATE, _mensaje(thread_ctx, body_redacted or "", subject))
    if not all(k in datos for k in ("es_os", "tipo_evento", "confidence")):
        raise HaikuSalidaInvalida("gate_campos_faltantes")
    detalle = datos.get("detalle")
    if isinstance(detalle, str):
        detalle = detalle[:MAX_DETALLE]
    else:
        detalle = None
    resultado = GateResult(
        es_os=datos["es_os"],
        tipo_evento=datos["tipo_evento"],
        confidence=datos["confidence"],
        detalle=detalle,
    )
    _log_ok("gate", datos, tipo_evento=resultado.tipo_evento, confidence=resultado.confidence)
    return resultado


def extract(body_redacted: str, thread_ctx: ThreadCtx, gate: Optional[GateResult] = None) -> list[RowExtraida]:
    # Con ``gate`` el tipo_evento ya decidido va en el mensaje; sin él, el
    # modelo lo infiere. validate.validar_rows exige coherencia con el gate.
    _exigir_redactado("extract", thread_ctx, body_redacted)
    if thread_ctx.filas is None and thread_ctx.etapa != "init":
        raise ProveedorNoDisponible("haiku_filas_no_cargadas")
    datos = _llamar("extract", _SCHEMA_EXTRACT, _mensaje(thread_ctx, body_redacted or "", gate=gate))
    filas = datos.get("rows")
    if not isinstance(filas, list):
        raise HaikuSalidaInvalida("extract_rows_no_lista")
    rows = []
    for fila in filas:
        if not isinstance(fila, dict) or "accion" not in fila:
            raise HaikuSalidaInvalida("extract_fila_invalida")
        rows.append(RowExtraida(
            accion=fila["accion"],
            row_number=fila.get("row_number"),
            **{campo: fila.get(campo) for campo in CAMPOS_FILA},
        ))
    _log_ok("extract", datos, filas=len(rows))
    return rows

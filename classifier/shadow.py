"""Modo sombra: corre un segundo proveedor sobre el mismo correo y solo lo registra.

* ``CLASSIFIER_SHADOW`` (opcional, vacía por defecto): nombre del proveedor
  sombra (p. ej. ``haiku``). Solo corre si es distinto del gate activo
  (``CLASSIFIER_GATE``).
* Candado: una sombra externa solo corre si ``registry.redaccion_apta()``
  (``REDACT_VERSION >= 2``, ver ``classifier/registry.py``).
* ``CLASSIFIER_SHADOW_SAMPLE`` (opcional, 0.0-1.0, default 1.0): fracción de
  correos que se mandan a la sombra, para controlar costo.

Su resultado NUNCA afecta el flujo: no bloquea, no aplica nada y no manda
correos. Corre en un thread daemon después de la decisión real, con un
timeout corto (``TIMEOUT_S``), y no propaga excepciones. Antes de un
proveedor externo se aplica la misma redacción que en producción
(``registry.get_redactor``, conservando las series del hilo); si falla, no
hay llamada y queda el motivo. Con un gate activo ``regex`` el contexto del
hilo no se cargó para la decisión real: la sombra lo carga en su thread con
el cargador registrado, igual que lo vería el proveedor en producción.

Registro: una línea por correo a stdout (Cloud Logging) con el prefijo fijo
``[CLASSIFIER_SHADOW]`` y un JSON con: hash del message_id (sha256
truncado), customer, etapa, dirección, decisión real y sombra (proveedor,
es_os, tipo_evento, confidence; la sombra además ``motivo_caida``), si
coinciden (es_os y tipo_evento), latencia_ms de la sombra y versión de
prompt. Nunca texto del correo, asunto, series, folios, nombres ni correos.
El reporte está en ``eval/shadow_report.py``.

Límite: el gate de ``init`` de Danone y Penafiel se decide dentro del parser
(``gate_proposito``, sin el ``Message``); esa decisión no pasa por aquí.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import threading
import time
from typing import Optional

import classifier
from classifier import registry, validate
from classifier.contracts import ETAPA_REPLY, PROVEEDOR_REGEX, GateResult, ThreadCtx

PREFIJO = "[CLASSIFIER_SHADOW]"
TIMEOUT_S = 10.0
LARGO_HASH = 16


def nombre_sombra() -> Optional[str]:
    nombre = (os.getenv("CLASSIFIER_SHADOW") or "").strip().lower()
    return nombre or None


def muestra() -> float:
    valor = os.getenv("CLASSIFIER_SHADOW_SAMPLE")
    if not valor:
        return 1.0
    try:
        return min(1.0, max(0.0, float(valor)))
    except ValueError:
        return 1.0


def hash_id(message_id) -> Optional[str]:
    if not message_id:
        return None
    return hashlib.sha256(str(message_id).encode("utf-8")).hexdigest()[:LARGO_HASH]


def _resumen(proveedor, gate: Optional[GateResult]) -> dict:
    conf = getattr(gate, "confidence", None)
    return {
        "proveedor": proveedor,
        "es_os": getattr(gate, "es_os", None),
        "tipo_evento": getattr(gate, "tipo_evento", None),
        "confidence": round(conf, 3) if isinstance(conf, (int, float)) and not isinstance(conf, bool) else None,
    }


def _version_prompt(modulo) -> Optional[str]:
    fn = getattr(modulo, "version_prompt", None)
    if fn is None:
        return None
    try:
        return fn("gate")
    except Exception:
        return None


def evaluar(nombre: str, email, subject, body, ctx: ThreadCtx) -> dict:
    """Corre el gate sombra. ``{"gate", "motivo", "prompt_version"}``; nunca
    lanza. ``motivo`` es un código sin PII (validación o clase de error)."""
    salida = {"gate": None, "motivo": None, "prompt_version": None}
    try:
        modulo = registry.cargar(nombre)
        salida["prompt_version"] = _version_prompt(modulo)
        if nombre != PROVEEDOR_REGEX:
            cargador = classifier._cargador_contexto
            if cargador is not None and ctx.filas is None and ctx.etapa == ETAPA_REPLY:
                try:
                    ctx = cargador(email, ctx)
                except Exception:
                    pass  # el proveedor ve "filas no se cargaron"
            try:
                redact = registry.get_redactor()
                conservar = ctx.series()
                subject = redact(subject, conservar=conservar) if subject else subject
                body = redact(body or "", conservar=conservar)
            except Exception:
                salida["motivo"] = "redaccion_error"
                return salida
        gate = modulo.gate(subject, body, ctx)
        if isinstance(gate, GateResult):
            salida["gate"] = gate
        errores = validate.validar_gate(gate, ctx, registry.min_confidence())
        if errores:
            salida["motivo"] = ",".join(errores)
    except Exception as e:
        salida["motivo"] = classifier._codigo_error(e)
    return salida


def _correr(nombre, email, subject, body, ctx, decision, mid_hash) -> None:
    try:
        t0 = time.monotonic()
        caja: dict = {}
        hilo = threading.Thread(
            target=lambda: caja.update(evaluar(nombre, email, subject, body, ctx)),
            name="classifier-shadow-call",
            daemon=True,
        )
        hilo.start()
        hilo.join(TIMEOUT_S)
        latencia_ms = int((time.monotonic() - t0) * 1000)
        if hilo.is_alive() or not caja:
            caja = {"gate": None, "motivo": "shadow_timeout", "prompt_version": None}

        sombra = _resumen(nombre, caja["gate"])
        sombra["motivo_caida"] = caja["motivo"]
        real = _resumen(decision.proveedor_gate, decision.gate)
        coinciden = None
        if caja["gate"] is not None:
            coinciden = sombra["es_os"] == real["es_os"] and sombra["tipo_evento"] == real["tipo_evento"]

        registro = {
            "message_id_hash": mid_hash,
            "customer": ctx.customer,
            "etapa": ctx.etapa,
            "direccion": ctx.direccion,
            "real": real,
            "sombra": sombra,
            "coinciden": coinciden,
            "latencia_ms": latencia_ms,
            "prompt_version": caja["prompt_version"],
        }
        print(f"{PREFIJO} {json.dumps(registro, ensure_ascii=False, sort_keys=True)}", flush=True)
    except Exception as e:
        print(f"{PREFIJO}[ERROR] {type(e).__name__}", flush=True)


def lanzar(email, decision, ctx: Optional[ThreadCtx]) -> Optional[threading.Thread]:
    """Arranca la sombra en un thread daemon (o nada). Nunca lanza ni espera.
    Devuelve el thread (para pruebas) o None si no corre."""
    try:
        nombre = nombre_sombra()
        if nombre is None or decision is None or ctx is None:
            return None
        if nombre == registry.nombre_gate():
            return None
        if nombre != PROVEEDOR_REGEX and not registry.redaccion_apta("CLASSIFIER_SHADOW"):
            return None
        if random.random() >= muestra():
            return None
        subject = getattr(email, "subject", None)
        body = getattr(getattr(email, "unique_body", None), "content", None)
        mid = getattr(email, "internet_message_id", None) or getattr(email, "id", None)
        hilo = threading.Thread(
            target=_correr,
            args=(nombre, email, subject, body, ctx, decision, hash_id(mid)),
            name="classifier-shadow",
            daemon=True,
        )
        hilo.start()
        return hilo
    except Exception as e:
        print(f"{PREFIJO}[ERROR] {type(e).__name__}", flush=True)
        return None

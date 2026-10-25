"""Contratos de la capa de lectura del cuerpo del correo (Fase 3).

Este módulo solo define tipos y reglas. No llama a nada externo.

Piezas
======

``gate(subject, body_redacted, thread_ctx) -> GateResult``
    Decide si el correo es una orden de servicio (OS) y qué evento representa.
    ``tipo_evento`` es un enum cerrado (``TIPOS_EVENTO``):

    * ``nueva_solicitud``: primer correo de una solicitud (etapa ``init``).
    * ``agregar_filas``, ``modificar_filas``, ``cancelar_filas``: un mensaje de
      hilo que cambia filas de ``cooler_request``.
    * ``cancelar_solicitud``: cancela la solicitud completa.
    * ``estatus``: consulta o acción administrativa sin filas (``bot.estatus``,
      ``bot.ayuda``, ``bot.global``, ``bot.finalizar``...).
    * ``duplicado``: el mismo pedido ya llegó.
    * ``no_os``: el correo no pide nada (agradecimiento, confirmación...).

    Coherencia obligatoria: ``es_os`` es False solo con ``no_os`` o
    ``duplicado``. ``confidence`` va de 0 a 1.

``extract(body_redacted, thread_ctx) -> list[RowExtraida]``
    Solo si ``es_os``. Devuelve las filas que el texto pide crear, cambiar o
    cancelar. ``row_number`` identifica una fila ya guardada y es obligatorio
    para ``modificar`` y ``cancelar``. El proveedor ``regex`` devuelve ``[]``:
    hoy las filas salen del Excel.

``thread_ctx`` (``ThreadCtx``)
    Lo que se sabe del hilo antes de leer el correo: etapa (``init`` o
    ``reply``), cliente, dirección, decisiones previas del hilo y filas ya
    guardadas en ``cooler_request`` (``row_number``, series y ``status``).
    ``filas=None`` significa "no se cargaron" (no "no hay filas"): ninguna
    referencia a una fila existente se puede validar y la extracción cae a
    ``regex``.

``redact(text) -> str``
    La implementa otra sesión en ``classifier/redact.py``. Se aplica al asunto
    y al cuerpo ANTES de cualquier proveedor que no sea ``regex``. El
    proveedor ``regex`` corre local y recibe el texto original. Mientras
    ``redact.py`` no exista, el stub de ``classifier.registry`` lanza
    ``NotImplementedError`` y la decisión cae a ``regex``.

Proveedores
===========

Se eligen con ``CLASSIFIER_GATE`` y ``CLASSIFIER_EXTRACT`` (opcionales,
default ``regex``). Un proveedor es un módulo en ``classifier/providers/`` con
``NAME``, ``gate(...)`` y ``extract(...)`` con las firmas de arriba
(``GateProvider`` y ``ExtractProvider``). ``haiku`` y ``jev`` están
registrados pero no implementados aquí.

Si un proveedor externo falla, no está disponible o su salida no pasa
``classifier.validate``, la decisión cae a ``regex`` y queda un log sin PII
(solo códigos de error, nombres de campo e índices).

Reglas de negocio (decididas por el usuario el 2026-10-25)
==========================================================

* Modificar o cancelar una fila ``ACCEPTED`` NUNCA se aplica automáticamente:
  se marca para revisión humana con el comentario ``"requiere revisión"``
  (``COMENTARIO_REVISION``). Aplica igual a ``cancelar_solicitud``: las filas
  ACCEPTED de la solicitud van a revisión.
* Las filas ``PENDING`` sí se pueden modificar o cancelar.
* Filas en otro estado (``CANCELLED``, ``REJECTED``): no hay decisión de
  negocio; por precaución también van a revisión (``motivo``
  ``estado_no_pending``).
* Esta capa solo EXPONE qué filas requieren revisión
  (``Decision.filas_revision``). El canal de revisión lo implementa otra
  sesión.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional, Protocol, Sequence

# ------------------------------------------------------------------ enums
NUEVA_SOLICITUD = "nueva_solicitud"
AGREGAR_FILAS = "agregar_filas"
MODIFICAR_FILAS = "modificar_filas"
CANCELAR_FILAS = "cancelar_filas"
CANCELAR_SOLICITUD = "cancelar_solicitud"
ESTATUS = "estatus"
DUPLICADO = "duplicado"
NO_OS = "no_os"

TIPOS_EVENTO = (
    NUEVA_SOLICITUD,
    AGREGAR_FILAS,
    MODIFICAR_FILAS,
    CANCELAR_FILAS,
    CANCELAR_SOLICITUD,
    ESTATUS,
    DUPLICADO,
    NO_OS,
)

# tipo_evento con es_os=False. Todos los demás implican es_os=True.
TIPOS_SIN_OS = frozenset({NO_OS, DUPLICADO})

# Eventos que solo tienen sentido dentro de un hilo con solicitud.
TIPOS_DE_HILO = frozenset({
    AGREGAR_FILAS, MODIFICAR_FILAS, CANCELAR_FILAS, CANCELAR_SOLICITUD, ESTATUS,
})

AGREGAR = "agregar"
MODIFICAR = "modificar"
CANCELAR = "cancelar"
ACCIONES = (AGREGAR, MODIFICAR, CANCELAR)

# Acción de fila permitida por cada tipo_evento con filas.
ACCION_POR_TIPO = {
    NUEVA_SOLICITUD: AGREGAR,
    AGREGAR_FILAS: AGREGAR,
    MODIFICAR_FILAS: MODIFICAR,
    CANCELAR_FILAS: CANCELAR,
}

PENDING = "PENDING"
ACCEPTED = "ACCEPTED"
CANCELLED = "CANCELLED"
REJECTED = "REJECTED"
STATUS_FILA = (PENDING, ACCEPTED, CANCELLED, REJECTED)

ETAPA_INIT = "init"
ETAPA_REPLY = "reply"
ETAPAS = (ETAPA_INIT, ETAPA_REPLY)

COMENTARIO_REVISION = "requiere revisión"

PROVEEDOR_REGEX = "regex"

# Campos de texto de una fila extraída, en el orden del contrato.
CAMPOS_FILA = (
    "folio",
    "serie_fabricante",
    "serie_dnn_bnf",
    "modelo",
    "tipo_servicio",
    "direccion",
)


# ------------------------------------------------------------------ tipos
@dataclass(frozen=True)
class GateResult:
    es_os: bool
    tipo_evento: str
    confidence: float
    # Pista corta y sin PII de por qué se decidió (p. ej. "bot.estatus",
    # "analizar_proposito"). Nunca texto del correo.
    detalle: Optional[str] = None


@dataclass(frozen=True)
class RowExtraida:
    accion: str
    folio: Optional[str] = None
    serie_fabricante: Optional[str] = None
    serie_dnn_bnf: Optional[str] = None
    modelo: Optional[str] = None
    tipo_servicio: Optional[str] = None
    direccion: Optional[str] = None
    # Solo si la fila se refiere a una ya guardada en cooler_request.
    row_number: Optional[int] = None


@dataclass(frozen=True)
class FilaGuardada:
    """Fila de ``cooler_request`` que el hilo ya tiene."""

    row_number: int
    status: str
    serie_fabricante: Optional[str] = None
    serie_dnn_bnf: Optional[str] = None


@dataclass(frozen=True)
class DecisionPrevia:
    """Decisión ya tomada en el mismo hilo. Sin texto del correo."""

    tipo_evento: str
    es_os: bool
    proveedor: str


@dataclass(frozen=True)
class ThreadCtx:
    etapa: str
    customer: Optional[str] = None
    # inbound, outbound, reply_to_bot o bot (solo en etapa reply).
    direccion: Optional[str] = None
    request_code: Optional[str] = None
    decisiones: tuple[DecisionPrevia, ...] = ()
    # None = no se cargaron; () = la solicitud no tiene filas.
    filas: Optional[tuple[FilaGuardada, ...]] = None

    def fila(self, row_number: int) -> Optional[FilaGuardada]:
        for fila in self.filas or ():
            if fila.row_number == row_number:
                return fila
        return None


@dataclass(frozen=True)
class FilaRevision:
    """Fila que NO se aplica automáticamente y va a revisión humana."""

    row_number: int
    accion: str
    status: str
    motivo: str  # "fila_accepted" o "estado_no_pending"
    comentario: str = COMENTARIO_REVISION


@dataclass(frozen=True)
class Decision:
    gate: GateResult
    proveedor_gate: str
    proveedor_extract: str
    rows: tuple[RowExtraida, ...] = ()
    # rows que se pueden aplicar automáticamente (agregar o filas PENDING).
    filas_aplicables: tuple[RowExtraida, ...] = ()
    filas_revision: tuple[FilaRevision, ...] = ()
    # Motivos (códigos sin PII) por los que se cayó a regex.
    fallbacks: tuple[str, ...] = field(default_factory=tuple)

    @property
    def es_os(self) -> bool:
        return self.gate.es_os

    @property
    def tipo_evento(self) -> str:
        return self.gate.tipo_evento

    @property
    def requiere_revision(self) -> bool:
        return bool(self.filas_revision)


# ------------------------------------------------------------------ interfaces
class GateProvider(Protocol):
    NAME: str

    def gate(self, subject: Optional[str], body_redacted: str, thread_ctx: ThreadCtx) -> GateResult:
        ...


class ExtractProvider(Protocol):
    NAME: str

    def extract(self, body_redacted: str, thread_ctx: ThreadCtx) -> Sequence[RowExtraida]:
        ...


# redact(text) -> str. Quita PII antes de mandar texto a un proveedor externo.
Redactor = Callable[[str], str]


class ProveedorNoDisponible(RuntimeError):
    """El proveedor está registrado pero no implementado o no se pudo cargar."""

"""Dobles de prueba del harness: repositorio en memoria, cliente de Graph,
Geocoding/Tableau y bloqueo de red.

Nada de este módulo toca código de producción: todo se inyecta con
``monkeypatch`` desde ``tests/conftest.py``.
"""

from __future__ import annotations

import importlib
import inspect
import socket
import sys
from types import SimpleNamespace
from typing import Any, Callable

from msgraph.generated.models.attachment_collection_response import (
    AttachmentCollectionResponse,
)
from msgraph.generated.models.file_attachment import FileAttachment
from msgraph.generated.models.message import Message

from tests.support.serialize import to_jsonable

# --------------------------------------------------------------------------
# Repositorio falso
# --------------------------------------------------------------------------

# (módulo, clase) que la producción usa como "repositorio".
REPOSITORY_CLASSES = (
    ("repository.danone.consultas_postgre", "DB_POSTGRE"),
    ("repository.gen.consultas_postgre", "DB_POSTGRE"),
    ("repository.penafiel.consultas_postgre", "DB_POSTGRE"),
    ("repository.heineken.consultas_postgre", "DB_HEINEKEN"),
    ("repository.holanda.consultas_postgre", "DB_HOLANDA"),
)

REQUEST_CODE_BASE = "REPARE_{:06d}"
EXISTING_REQUEST = {
    "request_code": "REPARE_000042",
    "link_email": "https://mail.example.com/thread/42",
}


# --------------------------------------------------------------------------
# Violaciones del harness
# --------------------------------------------------------------------------

# Producción envuelve casi todo en ``except Exception`` y se traga los errores.
# Por eso las violaciones (red, PostgreSQL, función del repo sin configurar)
# heredan de BaseException y además se anotan aquí: el fixture ``_offline``
# de conftest falla la prueba si la lista no quedó vacía.
VIOLATIONS: list[str] = []


class HarnessViolation(BaseException):
    """El código bajo prueba salió del entorno offline."""

    def __init__(self, message: str):
        VIOLATIONS.append(message)
        super().__init__(message)


class RepoBlocked(HarnessViolation):
    """Se intentó hablar con PostgreSQL de verdad."""


class UnconfiguredRepoCall(HarnessViolation):
    """Producción llamó una función del repositorio sin respuesta configurada."""


class NetworkBlocked(HarnessViolation):
    """Se intentó abrir una conexión de red."""


# Producción arma estas listas con ``SELECT DISTINCT`` (DuckDB) sin ORDER BY: el
# orden cambia entre corridas. Son conjuntos para el repositorio, así que se
# ordenan antes de registrarlas para que el golden sea determinista.
UNORDERED_PARAMS = {
    "get_equipos_con_caso_abierto": ("llaves",),
    "get_series_con_caso_abierto": ("series",),
    "get_request_codes_by_caso2": ("casos",),
}


class FakeRepo:
    """Repositorio en memoria.

    * Registra cada llamada (``module``, ``fn`` y parámetros por nombre).
    * Responde con valores por defecto sensatos que se pueden cambiar:

        fake_repo.set("get_email_request_status", "COMPLETED")
        fake_repo.set("email_reply_validate", lambda conversation_id, subject: None)
        fake_repo.queue("get_email_request_status", ["IN_PROGRESS", "COMPLETED"])
        fake_repo.fail("cancel_email_request", RuntimeError("db caída"))

    * Una función sin respuesta por defecto ni configuración lanza
      ``UnconfiguredRepoCall`` (BaseException): así un cambio en producción que
      empiece a usar otra función del repositorio se vuelve rojo en lugar de
      pasar en silencio.
    """

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self._responses: dict[str, Any] = {}
        self._queues: dict[str, list[Any]] = {}
        self._failures: dict[str, BaseException] = {}
        self._counter = 0
        self._serie_counter = 0
        self._defaults: dict[str, Any] = self._build_defaults()

    # ---- configuración -------------------------------------------------
    def set(self, fn: str, value: Any) -> None:
        """Valor fijo o ``callable(**params)`` para la función ``fn``."""
        self._responses[fn] = value

    def queue(self, fn: str, values: list[Any]) -> None:
        """Respuestas consecutivas; al agotarse se usa ``set``/default."""
        self._queues[fn] = list(values)

    def fail(self, fn: str, exc: BaseException) -> None:
        self._failures[fn] = exc

    # ---- consulta ------------------------------------------------------
    def calls_to(self, fn: str) -> list[dict[str, Any]]:
        return [c for c in self.calls if c["fn"] == fn]

    def names(self) -> list[str]:
        return [c["fn"] for c in self.calls]

    def snapshot(self) -> list[dict[str, Any]]:
        return to_jsonable(self.calls)

    # ---- defaults ------------------------------------------------------
    def _next_request_code(self, **_: Any) -> str:
        self._counter += 1
        return REQUEST_CODE_BASE.format(100 + self._counter)

    def _next_serie(self, prefijo: str, **_: Any) -> str:
        self._serie_counter += 1
        return f"{prefijo}20260101{self._serie_counter:05d}"

    @staticmethod
    def _distribuidora(cp: str, distribuidora: str = "", **_: Any):
        if str(cp).strip() == "99999":  # CP sin cobertura
            return None
        return {
            "codigo_postal": str(cp).strip(),
            "centro": "C001",
            "nombre_resp_pago": "RESP PAGO EJEMPLO",
            "distribuidora": "D001",
            "distribuidora_id": "D001 | DISTRIBUIDORA EJEMPLO",
        }

    def _build_defaults(self) -> dict[str, Any]:
        bot_status = {
            "request_code": EXISTING_REQUEST["request_code"],
            "status": "IN_PROGRESS",
            "total_coolers": 3,
            "completed_coolers": 1,
            "pending_coolers": 2,
            "failed_coolers": 0,
            "tickets_accepted": ["TCK-0001"],
            "tickets_pending": ["TCK-0002", "TCK-0003"],
            "tickets_cancelled": None,
        }
        totals = [
            {
                "total_coolers": 3,
                "completed_coolers": 2,
                "pending_coolers": 1,
                "failed_coolers": 0,
            }
        ]
        return {
            # --- DB_POSTGRE (danone / gen / penafiel) ---
            "get_available_catalog": {},
            "save_email_log_init": self._next_request_code,
            "consulta_link_email": None,
            "email_init_exist": False,
            "send_email_request": None,
            "send_email_coolers": None,
            "insert_update_cooler": None,
            "email_reply_validate": dict(EXISTING_REQUEST),
            "update_cooler": None,
            "update_email_request": None,
            "complete_email_request": [{"request_code": EXISTING_REQUEST["request_code"]}],
            "cancel_email_request": [{"request_code": EXISTING_REQUEST["request_code"]}],
            "get_email_request_status": "IN_PROGRESS",
            "cancel_pending_coolers": [],
            "get_total_coolers": totals,
            "conversation_exists": False,
            "email_request_bot_status": bot_status,
            "get_email_request_global": [],
            "get_distribuidora_mov": self._distribuidora,
            "get_distribuidora_ruta": self._distribuidora,
            # --- DB_HEINEKEN ---
            "get_series_con_caso_abierto": [],
            "guardar_casos": None,
            "conciliar": EXISTING_REQUEST["request_code"],
            "serie_generica_pendiente": None,
            "generar_serie_generica": self._next_serie,
            "get_request": {
                "request_code": EXISTING_REQUEST["request_code"],
                "status": "IN_PROGRESS",
            },
            "bot_status": bot_status,
            "global_status": [],
            # --- DB_HOLANDA ---
            "insert_coolers": None,
            "get_equipos_con_caso_abierto": [],
            "get_request_codes_by_caso2": [EXISTING_REQUEST["request_code"]],
            "update_os_by_caso2": None,
        }

    # ---- despacho ------------------------------------------------------
    def handle(self, module: str, fn: str, params: dict[str, Any]) -> Any:
        for name in UNORDERED_PARAMS.get(fn, ()):
            if isinstance(params.get(name), (list, tuple)):
                params[name] = sorted(params[name])
        self.calls.append({"module": module, "fn": fn, "params": to_jsonable(params)})

        if fn in self._failures:
            raise self._failures[fn]

        queue = self._queues.get(fn)
        if queue:
            value = queue.pop(0)
        elif fn in self._responses:
            value = self._responses[fn]
        elif fn in self._defaults:
            value = self._defaults[fn]
        else:
            raise UnconfiguredRepoCall(
                f"FakeRepo no tiene respuesta para '{fn}': configúrala con "
                f"fake_repo.set('{fn}', ...) en tests/conftest.py o en la prueba."
            )

        if callable(value):
            return value(**params)
        # Copia superficial para que producción no mute el default.
        if isinstance(value, dict):
            return dict(value)
        if isinstance(value, list):
            return [dict(v) if isinstance(v, dict) else v for v in value]
        return value


def _wrap(repo: FakeRepo, module: str, cls_name: str, name: str, original: Callable):
    signature = inspect.signature(original)
    label = f"{module.rsplit('.', 2)[-2]}.{cls_name}"

    def wrapper(*args, **kwargs):
        try:
            bound = signature.bind(*args, **kwargs)
            params = dict(bound.arguments)
        except TypeError:
            params = {"args": list(args), **kwargs}
        return repo.handle(label, name, params)

    wrapper.__name__ = name
    return staticmethod(wrapper)


def install_fake_repo(monkeypatch, repo: FakeRepo) -> None:
    """Reemplaza cada función pública de ``repository.*`` por el doble."""
    for module_name, cls_name in REPOSITORY_CLASSES:
        module = importlib.import_module(module_name)
        cls = getattr(module, cls_name)
        for name, member in list(vars(cls).items()):
            if name.startswith("_"):
                continue
            func = member.__func__ if isinstance(member, staticmethod) else member
            if not callable(func):
                continue
            monkeypatch.setattr(cls, name, _wrap(repo, module_name, cls_name, name, func))


# --------------------------------------------------------------------------
# Bloqueo de PostgreSQL / Secret Manager y de la red
# --------------------------------------------------------------------------

def block_database(monkeypatch) -> None:
    """Cualquier ``execute_query``/``get_connection`` real falla fuerte."""
    import infrastructure.database.postgres as postgres

    def _blocked_query(*_a, **_k):
        raise RepoBlocked("execute_query real bloqueado: usa el FakeRepo o patchea execute_query")

    def _blocked_conn(*_a, **_k):
        raise RepoBlocked("get_connection real bloqueado: el harness es offline")

    original = postgres.execute_query
    monkeypatch.setattr(postgres, "get_connection", _blocked_conn)
    monkeypatch.setattr(postgres, "execute_query", _blocked_query)
    for module in list(sys.modules.values()):
        if getattr(module, "execute_query", None) is original:
            monkeypatch.setattr(module, "execute_query", _blocked_query)


def block_network(monkeypatch) -> None:
    """Bloquea sockets salientes (los AF_UNIX del event loop siguen vivos)."""
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex

    def _blocked(*_a, **_k):
        raise NetworkBlocked("el harness es offline: conexión de red bloqueada")

    def connect(self, address):
        if self.family == getattr(socket, "AF_UNIX", None):
            return real_connect(self, address)
        return _blocked()

    def connect_ex(self, address):
        if self.family == getattr(socket, "AF_UNIX", None):
            return real_connect_ex(self, address)
        return _blocked()

    monkeypatch.setattr(socket.socket, "connect", connect)
    monkeypatch.setattr(socket.socket, "connect_ex", connect_ex)
    monkeypatch.setattr(socket, "create_connection", _blocked)
    monkeypatch.setattr(socket, "getaddrinfo", _blocked)
    monkeypatch.setattr(socket, "gethostbyname", _blocked)


# --------------------------------------------------------------------------
# Servicios externos: Geocoding (Google), Tableau
# --------------------------------------------------------------------------

class FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code
        self.text = str(payload)

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeExternals:
    """Registra las llamadas a servicios externos y responde offline."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        # latlng -> payload; si no está, respuesta genérica determinista.
        self.geocode_overrides: dict[str, dict] = {}

    def snapshot(self) -> list[dict[str, Any]]:
        return to_jsonable(self.calls)

    # Google Geocoding (requests.get)
    def geocode_payload(self, latlng: str) -> dict:
        if latlng in self.geocode_overrides:
            return self.geocode_overrides[latlng]
        return {
            "status": "OK",
            "results": [
                {
                    "formatted_address": "Calle Ficticia 100, Colonia Ejemplo, 06000, México",
                    "address_components": [
                        {"long_name": "06000", "types": ["postal_code"]},
                        {"long_name": "Colonia Ejemplo", "types": ["sublocality", "political"]},
                        {"long_name": "Ciudad Ejemplo", "types": ["locality", "political"]},
                        {"long_name": "Estado Ejemplo", "types": ["administrative_area_level_1", "political"]},
                        {"long_name": "México", "types": ["country", "political"]},
                        {"long_name": "Calle Ficticia", "types": ["route"]},
                    ],
                }
            ],
        }

    def requests_get(self, url, params=None, **_kwargs):
        if "maps.googleapis.com/maps/api/geocode" not in str(url):
            raise NetworkBlocked(f"requests.get a {url!r} bloqueado por el harness")
        params = dict(params or {})
        latlng = str(params.get("latlng", ""))
        self.calls.append({"service": "google_geocoding", "latlng": latlng})
        return FakeResponse(self.geocode_payload(latlng))

    # Tableau
    def tableau(self, name: str) -> Callable:
        def fake(*args, **kwargs):
            self.calls.append({"service": "tableau", "fn": name, "args": to_jsonable(args)})
            return []

        fake.__name__ = name
        return fake


def install_externals(monkeypatch, externals: FakeExternals) -> None:
    import requests

    monkeypatch.setattr(requests, "get", externals.requests_get)

    def _blocked_http(*_a, **_k):
        raise NetworkBlocked("requests.post/put/patch/request bloqueados por el harness")

    for verb in ("post", "put", "patch", "delete", "request"):
        monkeypatch.setattr(requests, verb, _blocked_http)
    monkeypatch.setattr(requests.Session, "request", _blocked_http)

    # Tableau: se importa por nombre en varios módulos -> se reemplaza cada referencia.
    import infrastructure.tableau.tableau as tableau

    for name in ("getToken", "getPtoVentaData", "getModelo", "get_modelo_act_ser"):
        original = getattr(tableau, name, None)
        if original is None:
            continue
        fake = externals.tableau(name)
        for module in list(sys.modules.values()):
            if getattr(module, name, None) is original:
                monkeypatch.setattr(module, name, fake)


# --------------------------------------------------------------------------
# Microsoft Graph falso
# --------------------------------------------------------------------------

class _Awaitable:
    """Envuelve un valor en algo que se pueda ``await``-ear sin event loop propio."""

    def __init__(self, fn: Callable[[], Any]):
        self._fn = fn

    def __await__(self):
        async def _run():
            return self._fn()

        return _run().__await__()


class FakeGraph:
    """Imita la cadena ``client.users.by_user_id(u).messages.by_message_id(m)``.

    * ``add_message(message, attachments)`` registra correos entrantes.
    * Las respuestas del bot (``create_reply`` → ``patch`` → ``attachments.post``
      → ``send``) quedan en ``self.sent``.
    """

    def __init__(self) -> None:
        self.messages: dict[str, Message] = {}
        self.attachments: dict[str, list[FileAttachment]] = {}
        self.calls: list[dict[str, Any]] = []
        self._drafts: dict[str, dict[str, Any]] = {}
        self.sent: list[dict[str, Any]] = []
        self._draft_counter = 0

    # ---- armado --------------------------------------------------------
    def add_message(self, message: Message, attachments: list[tuple[str, bytes]] | None = None) -> None:
        self.messages[message.id] = message
        self.attachments[message.id] = [
            FileAttachment(
                odata_type="#microsoft.graph.fileAttachment",
                id=f"att-{message.id}-{i}",
                name=name,
                content_bytes=content,
            )
            for i, (name, content) in enumerate(attachments or [], start=1)
        ]

    # ---- cliente -------------------------------------------------------
    @property
    def users(self):
        return _Users(self)

    def log(self, op: str, **data: Any) -> None:
        self.calls.append({"op": op, **to_jsonable(data)})


class _Users:
    def __init__(self, graph: FakeGraph):
        self._graph = graph

    def by_user_id(self, user_id: str):
        return SimpleNamespace(messages=_Messages(self._graph, user_id))


class _Messages:
    def __init__(self, graph: FakeGraph, user_id: str):
        self._graph = graph
        self._user_id = user_id

    def by_message_id(self, message_id: str):
        return _Message(self._graph, self._user_id, message_id)


class _Message:
    def __init__(self, graph: FakeGraph, user_id: str, message_id: str):
        self._g = graph
        self._user_id = user_id
        self._id = message_id

    # GET del correo
    def get(self, request_configuration=None):
        def run():
            self._g.log("get_message", message_id=self._id)
            if self._id not in self._g.messages:
                raise LookupError(f"FakeGraph: mensaje {self._id!r} no registrado")
            return self._g.messages[self._id]

        return _Awaitable(run)

    @property
    def attachments(self):
        return _Attachments(self._g, self._id)

    @property
    def create_reply(self):
        return _CreateReply(self._g, self._id)

    def patch(self, body):
        def run():
            draft = self._g._drafts[self._id]
            if getattr(body, "body", None) is not None:
                draft["body"] = body.body.content
            recipients = getattr(body, "to_recipients", None)
            if recipients is not None:
                draft["to"] = [r.email_address.address for r in recipients]
            self._g.log("patch_draft", draft_id=self._id)
            return body

        return _Awaitable(run)

    @property
    def send(self):
        return _Send(self._g, self._id)


class _Attachments:
    def __init__(self, graph: FakeGraph, message_id: str):
        self._g = graph
        self._id = message_id

    def get(self):
        def run():
            self._g.log("list_attachments", message_id=self._id)
            return AttachmentCollectionResponse(value=list(self._g.attachments.get(self._id, [])))

        return _Awaitable(run)

    def post(self, attachment):
        def run():
            draft = self._g._drafts[self._id]
            draft["attachments"].append((attachment.name, attachment.content_bytes))
            self._g.log("add_attachment", draft_id=self._id, name=attachment.name)
            return attachment

        return _Awaitable(run)


class _CreateReply:
    def __init__(self, graph: FakeGraph, message_id: str):
        self._g = graph
        self._id = message_id

    def post(self, _body=None):
        def run():
            self._g._draft_counter += 1
            draft_id = f"draft-{self._g._draft_counter}"
            self._g._drafts[draft_id] = {
                "in_reply_to": self._id,
                "to": [],
                "body": None,
                "attachments": [],
            }
            self._g.log("create_reply", message_id=self._id, draft_id=draft_id)
            return Message(id=draft_id)

        return _Awaitable(run)


class _Send:
    def __init__(self, graph: FakeGraph, draft_id: str):
        self._g = graph
        self._id = draft_id

    def post(self):
        def run():
            draft = self._g._drafts[self._id]
            self._g.sent.append(draft)
            self._g.log("send", draft_id=self._id)
            return None

        return _Awaitable(run)

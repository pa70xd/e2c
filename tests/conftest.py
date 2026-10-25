"""Harness offline de e2c.

Qué hace este archivo (sin tocar código de producción):

* Aísla el entorno ANTES de importar producción: ``DEBUG=false`` y un
  directorio de trabajo temporal con enlaces a ``config/`` y
  ``excel_templates/`` (producción lee rutas relativas al cwd y crea
  ``Documentos_Adjuntos/``; así el repo no se ensucia).
* Bloquea sockets y PostgreSQL en TODAS las pruebas. Si un golden intenta
  conectarse, falla (es un bug del harness, no algo que se deba ignorar).
* Ofrece el fixture ``harness``: repositorio falso en memoria, Graph falso,
  Geocoding/Tableau falsos y buzones de REPARE inventados.
* Ofrece el fixture ``golden`` (``--update-golden`` para regenerar).
"""

from __future__ import annotations

import asyncio
import atexit
import difflib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

# --- 1. entorno aislado (antes de importar cualquier módulo de producción) ---
REPO_ROOT = Path(__file__).resolve().parents[1]
GOLDEN_DIR = Path(__file__).resolve().parent / "golden"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

os.environ["DEBUG"] = "false"

# Sin credenciales: aunque alguien tenga un .env o variables reales, ninguna
# llega a producción. (Además la red y PostgreSQL están bloqueados.)
for _var in (
    "SECRET_PG_ACC", "DB_HOST", "DB_NAME", "DB_PORT",
    "CLIENT_ID", "CLIENT_SECRET", "TENANT_ID", "PROJECT_ID",
    "MAPS_KEY", "GOOGLE_MAPS_API_KEY", "REPARE_BUCKET", "MAIL",
):
    os.environ.pop(_var, None)

_WORKDIR = Path(tempfile.mkdtemp(prefix="e2c-tests-"))
for _name in ("config", "excel_templates"):
    (_WORKDIR / _name).symlink_to(REPO_ROOT / _name, target_is_directory=True)
atexit.register(shutil.rmtree, _WORKDIR, ignore_errors=True)

# Producción lee rutas relativas al cwd al IMPORTAR (config/email_index.json) y
# al ejecutar. Se importa desde el directorio de trabajo temporal y se regresa
# al cwd original para no alterar cómo pytest resuelve ``testpaths``; cada
# prueba corre dentro del directorio temporal (ver ``_offline``).
_ORIGINAL_CWD = os.getcwd()
os.chdir(_WORKDIR)

import pytest  # noqa: E402

from tests.support import emails as emails_mod  # noqa: E402
from tests.support.fakes import (  # noqa: E402
    VIOLATIONS,
    FakeExternals,
    FakeGraph,
    FakeRepo,
    block_database,
    block_network,
    install_externals,
    install_fake_repo,
)
from tests.support.serialize import summarize_reply, to_jsonable  # noqa: E402

import src.service as service  # noqa: E402  (importar DESPUÉS del chdir)

os.chdir(_ORIGINAL_CWD)


# --------------------------------------------------------------------------
# opciones
# --------------------------------------------------------------------------

def pytest_addoption(parser):
    parser.addoption(
        "--update-golden",
        action="store_true",
        default=False,
        help="Reescribe tests/golden/*.json con el comportamiento actual en lugar de compararlo.",
    )


# --------------------------------------------------------------------------
# bloqueo global: ninguna prueba toca red ni PostgreSQL
# --------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.chdir(_WORKDIR)
    # Clasificador por defecto (regex) y sin llave de un proveedor externo.
    for var in ("CLASSIFIER_GATE", "CLASSIFIER_EXTRACT", "CLASSIFIER_MIN_CONFIDENCE", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    VIOLATIONS.clear()
    block_network(monkeypatch)
    block_database(monkeypatch)
    yield
    # Producción se traga las excepciones (``except Exception``); el registro
    # de violaciones garantiza que un intento de red/DB igual falle la prueba.
    violations = list(VIOLATIONS)
    VIOLATIONS.clear()
    assert not violations, "El harness es offline pero hubo intentos de salir: " + "; ".join(violations)


# --------------------------------------------------------------------------
# golden
# --------------------------------------------------------------------------

class Golden:
    def __init__(self, update: bool):
        self.update = update

    @staticmethod
    def render(data: Any) -> str:
        return json.dumps(data, indent=2, ensure_ascii=False) + "\n"

    def check(self, name: str, data: Any) -> None:
        path = GOLDEN_DIR / f"{name}.json"
        actual = self.render(to_jsonable(data))
        if self.update:
            GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
            path.write_text(actual, encoding="utf-8")
            return
        if not path.exists():
            pytest.fail(
                f"Falta el golden {path.relative_to(REPO_ROOT)}. "
                "Genéralo con: pytest --update-golden",
                pytrace=False,
            )
        expected = path.read_text(encoding="utf-8")
        if expected != actual:
            diff = "".join(
                difflib.unified_diff(
                    expected.splitlines(keepends=True),
                    actual.splitlines(keepends=True),
                    fromfile=f"golden/{name}.json",
                    tofile="actual",
                    n=2,
                )
            )
            pytest.fail(
                f"El comportamiento cambió respecto a golden/{name}.json.\n"
                "Si el cambio es intencional: pytest --update-golden y revisa el diff en git.\n\n"
                + diff[:6000],
                pytrace=False,
            )


@pytest.fixture
def golden(request) -> Golden:
    return Golden(request.config.getoption("--update-golden"))


# --------------------------------------------------------------------------
# harness del pipeline completo
# --------------------------------------------------------------------------

class Harness:
    """Corre ``src.service.processMail`` de punta a punta contra dobles."""

    def __init__(self, repo: FakeRepo, graph: FakeGraph, externals: FakeExternals):
        self.repo = repo
        self.graph = graph
        self.externals = externals
        self.deliveries: list[dict[str, Any]] = []

    # ---- correos -------------------------------------------------------
    def email(self, **kwargs):
        return emails_mod.make_email(**kwargs)

    def deliver(self, message, attachments: list[tuple[str, bytes]] | None = None):
        """Registra el correo en el Graph falso y lo procesa. Regresa el
        valor de ``processMail`` (o relanza su excepción)."""
        self.graph.add_message(message, attachments)
        sent_before = len(self.graph.sent)
        try:
            result = asyncio.run(service.processMail(emails_mod.notification(message)))
            error = None
        except Exception as exc:  # noqa: BLE001 - lo decide la prueba
            result, error = None, exc
        self.deliveries.append(
            {
                "message": {
                    "id": message.id,
                    "subject": message.subject,
                    "from": message.sender.email_address.address,
                    "to": [r.email_address.address for r in (message.to_recipients or [])],
                    "attachments": [n for n, _ in (attachments or [])],
                },
                "result": result,
                "error": None if error is None else f"{type(error).__name__}: {error}",
                "replies_sent": len(self.graph.sent) - sent_before,
            }
        )
        if error is not None:
            raise error
        return result

    # ---- salida --------------------------------------------------------
    @property
    def replies(self) -> list[dict[str, Any]]:
        return self.graph.sent

    def snapshot(self) -> dict[str, Any]:
        """Lo que se congela en tests/golden/*.json."""
        return {
            "deliveries": self.deliveries,
            "repo_calls": self.repo.snapshot(),
            "external_calls": self.externals.snapshot(),
            "replies": [summarize_reply(d) for d in self.graph.sent],
        }


@pytest.fixture
def harness(monkeypatch) -> Harness:
    repo, graph, externals = FakeRepo(), FakeGraph(), FakeExternals()

    install_fake_repo(monkeypatch, repo)
    install_externals(monkeypatch, externals)

    # Graph: processMail pide el cliente a través de este nombre.
    monkeypatch.setattr(service, "getClient", lambda: graph)

    # Buzones inventados en lugar de config/email_index.json (reales).
    monkeypatch.setattr(service.validator, "mailboxes", dict(emails_mod.MAILBOXES))
    monkeypatch.setattr(service, "CUSTOMER_INDEX", dict(emails_mod.MAILBOXES))
    # La ventana anti-duplicados (120 s) vive en memoria del proceso.
    monkeypatch.setattr(service.validator, "processed_emails", {})

    return Harness(repo, graph, externals)


# --------------------------------------------------------------------------
# fixtures de archivos sintéticos
# --------------------------------------------------------------------------

class ClientFixtures:
    def __init__(self, client: str):
        self.dir = FIXTURES_DIR / client
        self.correos = json.loads((self.dir / "correos.json").read_text(encoding="utf-8"))

    def xlsx(self, name: str) -> tuple[str, bytes]:
        """(nombre de adjunto, bytes) listo para ``harness.deliver``."""
        return name, (self.dir / name).read_bytes()


@pytest.fixture
def fixtures_for():
    return ClientFixtures


# Atajos de direcciones para armar correos de hilo.
@pytest.fixture
def mail():
    class _Mail:
        repare = staticmethod(lambda cliente: emails_mod.REPARE[cliente])
        cliente = staticmethod(lambda cliente: emails_mod.CLIENTES[cliente])

    return _Mail

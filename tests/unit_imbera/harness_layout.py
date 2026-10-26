"""Extiende el ``harness`` de tests/conftest.py para Imbera y Torrey sin
tocar tests/support/: buzones inventados y el repositorio
``repository.imbera`` reemplazado por el mismo FakeRepo."""

from __future__ import annotations

import importlib

import pytest

import src.service as service
from tests.support import emails as emails_mod
from tests.support.fakes import _wrap

BUZONES = {
    "imbera": "cliente.imbera@repare.example.com",
    "torrey": "cliente.torrey@repare.example.com",
}
CLIENTES = {
    "imbera": ("Contacto Imbera Ejemplo", "contacto@imbera-cliente.example.com"),
    "torrey": ("Contacto Torrey Ejemplo", "contacto@torrey-cliente.example.com"),
}
REPO_MODULO = "repository.imbera.consultas_postgre"

# Filas de cooler_request de la solicitud existente (get_cooler_rows).
FILAS_SOLICITUD = [
    {"row_number": 1, "serie_fabricante": "SER-IMB-0001", "serie_dnn_bnf": None, "status": "PENDING"},
    {"row_number": 2, "serie_fabricante": None, "serie_dnn_bnf": None, "status": "REJECTED"},
    {"row_number": 3, "serie_fabricante": "SER-IMB-0004", "serie_dnn_bnf": None, "status": "ACCEPTED"},
]


def instalar(harness, monkeypatch):
    for cliente, buzon in BUZONES.items():
        monkeypatch.setitem(service.validator.mailboxes, buzon, cliente)
        monkeypatch.setitem(service.CUSTOMER_INDEX, buzon, cliente)
        monkeypatch.setitem(emails_mod.MAILBOXES, buzon, cliente)
        monkeypatch.setitem(emails_mod.REPARE, cliente, buzon)
        monkeypatch.setitem(emails_mod.CLIENTES, cliente, CLIENTES[cliente])

    modulo = importlib.import_module(REPO_MODULO)
    cls = modulo.DB_POSTGRE
    for name, member in list(vars(cls).items()):
        if name.startswith("_"):
            continue
        func = member.__func__ if isinstance(member, staticmethod) else member
        if callable(func):
            monkeypatch.setattr(cls, name, _wrap(harness.repo, REPO_MODULO, "DB_POSTGRE", name, func))

    harness.repo.set("update_os_por_serie", 1)
    harness.repo.set("update_os_por_fila", 1)
    harness.repo.set("get_cooler_rows", [dict(f) for f in FILAS_SOLICITUD])
    return harness


@pytest.fixture
def harness_layout(harness, monkeypatch):
    return instalar(harness, monkeypatch)

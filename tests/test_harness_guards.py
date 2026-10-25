"""El harness es offline: estas pruebas demuestran que los bloqueos funcionan.

Un ``except Exception`` de producción NO puede esconder un intento de salir a la
red o a PostgreSQL: las violaciones heredan de BaseException y además se
registran (ver ``_offline`` en conftest.py)."""

import socket

import pytest
import requests

from tests.support.fakes import (
    VIOLATIONS,
    NetworkBlocked,
    RepoBlocked,
    UnconfiguredRepoCall,
)


@pytest.fixture
def expect_violation():
    """Marca una violación como esperada para que ``_offline`` no falle la prueba."""
    yield
    VIOLATIONS.clear()


def test_socket_saliente_bloqueado(expect_violation):
    with pytest.raises(NetworkBlocked):
        socket.create_connection(("example.com", 443), timeout=1)
    assert VIOLATIONS


def test_resolucion_dns_bloqueada(expect_violation):
    with pytest.raises(NetworkBlocked):
        socket.getaddrinfo("example.com", 443)


def test_requests_bloqueado(expect_violation):
    with pytest.raises(NetworkBlocked):
        requests.get("https://example.com/")
    with pytest.raises(NetworkBlocked):
        requests.post("https://example.com/", json={})


def test_postgres_bloqueado(expect_violation):
    from infrastructure.database.postgres import execute_query, get_connection

    with pytest.raises(RepoBlocked):
        execute_query("SELECT 1")
    with pytest.raises(RepoBlocked):
        get_connection()


def test_repositorio_real_bloqueado_aunque_se_importe_por_nombre(expect_violation):
    from repository.danone.consultas_postgre import execute_query

    with pytest.raises(RepoBlocked):
        execute_query("SELECT 1")


def test_la_violacion_no_se_traga_con_except_exception(expect_violation):
    try:
        try:
            socket.create_connection(("example.com", 80), timeout=1)
        except Exception:  # lo que hace producción
            pytest.fail("la violación fue atrapada por `except Exception`")
    except NetworkBlocked:
        pass


def test_funcion_del_repo_sin_configurar_falla_fuerte(harness, expect_violation):
    with pytest.raises(UnconfiguredRepoCall):
        harness.repo.handle("repository.test.DB", "funcion_inventada", {})


def test_el_golden_falla_si_produccion_intenta_conectarse(harness, monkeypatch, expect_violation):
    """El mismo mecanismo, de punta a punta: un parser que llame a la red
    revienta la prueba aunque el servicio atrape ``Exception``."""
    from src import service

    original = service.validator.validate_email

    def validate_y_conecta(email):
        try:
            socket.create_connection(("example.com", 80), timeout=1)
        except Exception:  # noqa: BLE001 - lo que haría producción
            pass
        return original(email)

    monkeypatch.setattr(service.validator, "validate_email", validate_y_conecta)

    with pytest.raises(NetworkBlocked):
        harness.deliver(
            harness.email(
                subject="Solicitud de servicios",
                body="Favor de realizar instalaciones",
                sender=("Contacto", "contacto@example.com"),
                to=["cliente.danone@repare.example.com"],
                message_id="msg-guard",
            )
        )


def test_entorno_sin_credenciales_y_sin_debug():
    """DEBUG=false (para congelar las rutas de PRODUCCIÓN: dedupe, conversation_exists,
    sin volcados a disco) pero sin ninguna credencial ni destino de base de datos."""
    import os

    assert os.environ["DEBUG"] == "false"
    for var in ("SECRET_PG_ACC", "DB_HOST", "CLIENT_SECRET", "MAPS_KEY", "GOOGLE_MAPS_API_KEY"):
        assert var not in os.environ


def test_repositorio_apunta_a_tablas_de_produccion_pero_todo_acceso_esta_bloqueado(expect_violation):
    """Sin DEBUG=true los módulos de repositorio nombran las tablas de producción.
    Eso es inofensivo aquí porque ``execute_query``/``get_connection`` están
    bloqueados y las funciones públicas se sustituyen por el FakeRepo."""
    import repository.danone.consultas_postgre as repo
    assert repo.EMAIL_REQUEST == "repare_email_parse.email_request"
    with pytest.raises(RepoBlocked):
        repo.DB_POSTGRE.update_email_request("REPARE_000001")

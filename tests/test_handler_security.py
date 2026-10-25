"""CORS_ALLOW_ORIGINS y GRAPH_CLIENT_STATE (ambas opcionales)."""
import importlib

import pytest
from fastapi.testclient import TestClient

import src.handler as handler_mod

BODY = {"value": [{"id": "1", "clientState": "ok"}, {"id": "2", "clientState": "bad"}, {"id": "3"}]}


@pytest.fixture
def procesados(monkeypatch):
    vistos = []

    async def falso(mail):
        vistos.append(mail["id"])

    monkeypatch.setattr(handler_mod, "processMail", falso)
    return vistos


@pytest.fixture
def client():
    import main
    return TestClient(main.app)


def test_handshake_responde_el_token(client, monkeypatch):
    for estado in (None, "ok"):
        monkeypatch.setattr(handler_mod, "GRAPH_CLIENT_STATE", estado)
        r = client.post("/receive_mail?validationToken=abc")
        assert (r.status_code, r.text) == (200, "abc")


def test_sin_client_state_procesa_todo(client, procesados, monkeypatch):
    monkeypatch.setattr(handler_mod, "GRAPH_CLIENT_STATE", None)
    r = client.post("/receive_mail", json=BODY)
    assert r.status_code == 200
    assert procesados == ["1", "2", "3"]


def test_con_client_state_descarta_los_que_no_coinciden(client, procesados, monkeypatch, capsys):
    monkeypatch.setattr(handler_mod, "GRAPH_CLIENT_STATE", "ok")
    r = client.post("/receive_mail", json=BODY)
    assert (r.status_code, r.text) == (200, "Correo recibido, procesando en background.")
    assert procesados == ["1"]
    assert "clientState no coincide" in capsys.readouterr().out


@pytest.fixture(autouse=True)
def _recarga_main_sin_cors_env(monkeypatch):
    # Al terminar cada test, `main` se recarga sin CORS_ALLOW_ORIGINS para no filtrar estado.
    yield
    monkeypatch.delenv("CORS_ALLOW_ORIGINS", raising=False)
    import main
    importlib.reload(main)


def _preflight(client):
    return client.options(
        "/receive_mail",
        headers={"Origin": "http://x.com", "Access-Control-Request-Method": "POST"},
    )


def test_cors_por_defecto_comodin_sin_credenciales(monkeypatch):
    monkeypatch.delenv("CORS_ALLOW_ORIGINS", raising=False)
    import main
    main = importlib.reload(main)
    r = _preflight(TestClient(main.app))
    assert r.headers["access-control-allow-origin"] == "*"
    assert "access-control-allow-credentials" not in r.headers


def test_cors_con_origenes_explicitos_y_credenciales(monkeypatch):
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "http://x.com, http://y.com")
    import main
    main = importlib.reload(main)
    c = TestClient(main.app)
    r = _preflight(c)
    assert r.headers["access-control-allow-origin"] == "http://x.com"
    assert r.headers["access-control-allow-credentials"] == "true"
    r = c.options("/receive_mail", headers={"Origin": "http://z.com", "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in r.headers

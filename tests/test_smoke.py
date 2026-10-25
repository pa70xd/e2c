"""Prueba de humo: la app importa y el handshake de Graph responde."""

from fastapi.testclient import TestClient


def test_import_main():
    import main

    assert main.app.version == "0.33"
    assert {"/receive_mail", "/lifecyclenotif"} <= set(main.app.openapi()["paths"])


def test_receive_mail_handshake_devuelve_el_validation_token():
    import main

    client = TestClient(main.app)
    respuesta = client.post("/receive_mail", params={"validationToken": "token-de-prueba-123"})

    assert respuesta.status_code == 200
    assert respuesta.text == "token-de-prueba-123"
    assert respuesta.headers["content-type"].startswith("text/plain")


def test_lifecyclenotif_handshake_devuelve_el_validation_token():
    import main

    client = TestClient(main.app)
    respuesta = client.post("/lifecyclenotif", params={"validationToken": "token-ciclo-456"})

    assert respuesta.status_code == 200
    assert respuesta.text == "token-ciclo-456"


def test_receive_mail_encola_un_procesamiento_por_notificacion(monkeypatch):
    """Sin token, cada elemento de ``value`` se procesa en background."""
    import main
    import src.handler as handler_module

    recibidos = []

    async def falso_process_mail(mail):
        recibidos.append(mail)

    monkeypatch.setattr(handler_module, "processMail", falso_process_mail)

    notificaciones = [
        {"resourceData": {"@odata.id": "Users/u1/Messages/m1", "id": "m1"}},
        {"resourceData": {"@odata.id": "Users/u1/Messages/m2", "id": "m2"}},
    ]
    respuesta = TestClient(main.app).post("/receive_mail", json={"value": notificaciones})

    assert respuesta.status_code == 200
    assert respuesta.text == "Correo recibido, procesando en background."
    assert recibidos == notificaciones

"""Pruebas unitarias de ``src/email_type.py``: validación, tipo de correo
(inicial / respuesta), cliente, dirección y ventana anti-duplicados."""

import json

import pytest
from msgraph.generated.models.internet_message_header import InternetMessageHeader

from src.email_type import EMAIL_TYPE
from tests.support.emails import CLIENTES, MAILBOXES, REPARE, make_email

DANONE_BOX = REPARE["danone"]
HEINEKEN_BOX = REPARE["heineken"]
CLIENTE_DANONE = CLIENTES["danone"]
OTRO = ("Persona Ajena", "ajena@otro-dominio.example.com")


@pytest.fixture
def validator(tmp_path):
    config = tmp_path / "mailboxes.json"
    config.write_text(json.dumps(MAILBOXES), encoding="utf-8")
    return EMAIL_TYPE(config_path=str(config))


def mail(subject="Solicitud de servicios", body="texto", **kw):
    kw.setdefault("sender", CLIENTE_DANONE)
    kw.setdefault("to", [DANONE_BOX])
    kw.setdefault("message_id", "msg-unit")
    return make_email(subject=subject, body=body, **kw)


def header(name, value):
    return InternetMessageHeader(name=name, value=value)


# ---------------------------------------------------------------- _load
def test_config_inexistente_falla_con_filenotfound(tmp_path):
    with pytest.raises(FileNotFoundError):
        EMAIL_TYPE(config_path=str(tmp_path / "no_existe.json"))


def test_los_buzones_se_cargan_en_minusculas(tmp_path):
    config = tmp_path / "m.json"
    config.write_text(json.dumps({"Cliente.X@Repare.Example.com": "danone"}), encoding="utf-8")
    assert EMAIL_TYPE(config_path=str(config)).mailboxes == {"cliente.x@repare.example.com": "danone"}


# ---------------------------------------------------------------- validate_email
def test_correo_inicial_es_no_reply(validator):
    assert validator.validate_email(mail()) == [True, "no-reply"]


@pytest.mark.parametrize("prefijo", ["Re: ", "RE: ", "rv: ", "FW: ", "Fwd: "])
def test_prefijos_de_respuesta_o_reenvio_son_reply(validator, prefijo):
    assert validator.validate_email(mail(subject=f"{prefijo}Solicitud")) == [True, "reply"]


@pytest.mark.parametrize("encabezado", ["In-Reply-To", "References"])
def test_encabezados_de_hilo_son_reply(validator, encabezado):
    msg = mail()
    msg.internet_message_headers = [header(encabezado, "<otro@mail.example.com>")]
    assert validator.validate_email(msg) == [True, "reply"]


def test_borrador(validator):
    msg = mail()
    msg.is_draft = True
    assert validator.validate_email(msg) == (False, "DRAFT")


@pytest.mark.parametrize("asunto", [None, "", "   "])
def test_asunto_vacio(validator, asunto):
    msg = mail()
    msg.subject = asunto
    assert validator.validate_email(msg) == (False, "EMPTY_SUBJECT")


def test_cuerpo_vacio(validator):
    msg = mail()
    msg.unique_body = None
    assert validator.validate_email(msg) == (False, "EMPTY_BODY")


def test_sin_fecha_de_recepcion(validator):
    msg = mail()
    msg.received_date_time = None
    assert validator.validate_email(msg) == (False, "MISSING_RECEIVED_DATE")


def test_mensaje_de_evento(validator):
    msg = mail()
    msg.odata_type = "#microsoft.graph.eventMessageRequest"
    assert validator.validate_email(msg) == (False, "EVENT_MESSAGE")


def test_remitente_ignorado(validator):
    msg = mail(sender=("Reporte", "errorreportingnotifications-noreply@google.com"))
    assert validator.validate_email(msg) == (False, "IGNORED_SENDER")


@pytest.mark.parametrize(
    "encabezado, valor, esperado",
    [
        ("Auto-Submitted", "auto-replied", True),
        ("Auto-Submitted", "no", False),
        ("Auto-Submitted", "", False),
        ("X-Auto-Response-Suppress", "All", True),
    ],
)
def test_encabezados_de_envio_automatico(validator, encabezado, valor, esperado):
    msg = mail()
    msg.internet_message_headers = [header(encabezado, valor)]
    resultado = validator.validate_email(msg)
    assert (resultado == (False, "AUTO_SUBMITTED")) is esperado


@pytest.mark.parametrize(
    "asunto, razon",
    [
        ("Automatic reply: vacaciones", "AUTO_REPLY"),
        ("Respuesta automática: fuera", "AUTO_REPLY"),
        ("Out of Office hasta el lunes", "AUTO_REPLY"),
        ("Fuera de la oficina", "AUTO_REPLY"),
        ("Undeliverable: Solicitud", "DELIVERY_FAILURE"),
        ("Delivery Status Notification (Failure)", "DELIVERY_FAILURE"),
        ("Mail delivery failed: returning message", "DELIVERY_FAILURE"),
        ("Read: Solicitud", "READ_RECEIPT"),
        ("Confirmación de lectura: Solicitud", "READ_RECEIPT"),
    ],
)
def test_asuntos_automaticos(validator, asunto, razon):
    assert validator.validate_email(mail(subject=asunto)) == (False, razon)


# ---------------------------------------------------------------- detect_customer
def test_cliente_por_destinatario(validator):
    assert validator.detect_customer(mail(to=[DANONE_BOX])) == "danone"


def test_cliente_por_copia(validator):
    assert validator.detect_customer(mail(to=[OTRO[1]], cc=[HEINEKEN_BOX])) == "heineken"


def test_cliente_por_remitente_si_no_hay_destinatario_repare(validator):
    msg = mail(sender=("Operador", DANONE_BOX), to=[OTRO[1]])
    assert validator.detect_customer(msg) == "danone"


def test_cliente_desconocido(validator):
    assert validator.detect_customer(mail(sender=OTRO, to=[OTRO[1]])) is None


def test_cliente_ignora_mayusculas_y_espacios(validator):
    assert validator.detect_customer(mail(to=[f"  {DANONE_BOX.upper()} "])) == "danone"


# ---------------------------------------------------------------- detect_direccion
OPERADOR = ("Operador REPARE Ejemplo", DANONE_BOX)


def test_direccion_inbound(validator):
    assert validator.detect_direccion(mail()) == ("danone", "inbound")


def test_direccion_outbound(validator):
    msg = mail(sender=OPERADOR, to=[CLIENTE_DANONE[1]])
    assert validator.detect_direccion(msg) == ("danone", "outbound")


def test_direccion_reply_to_bot(validator):
    msg = mail(sender=OPERADOR, to=[DANONE_BOX], body="bot.estatus")
    assert validator.detect_direccion(msg) == ("danone", "reply_to_bot")


def test_direccion_bot_por_frase_de_plantilla(validator):
    msg = mail(sender=OPERADOR, to=[DANONE_BOX], body="Estimado   usuario\nREPARE, aviso")
    assert validator.detect_direccion(msg) == ("danone", "bot")


def test_direccion_frase_de_plantilla_de_cliente_sigue_siendo_inbound(validator):
    msg = mail(body="estimado usuario repare, gracias")
    assert validator.detect_direccion(msg) == ("danone", "inbound")


def test_direccion_con_destinatario_de_otro_cliente_usa_el_buzon_destino(validator):
    msg = mail(to=[HEINEKEN_BOX])
    assert validator.detect_direccion(msg) == ("heineken", "inbound")


# ---------------------------------------------------------------- is_duplicate_email
def test_duplicado_dentro_de_la_ventana(validator, monkeypatch):
    reloj = {"t": 1000.0}
    monkeypatch.setattr("src.email_type.time.time", lambda: reloj["t"])
    msg = mail(message_id="msg-dup")

    assert validator.is_duplicate_email(msg) is False
    reloj["t"] += 119
    assert validator.is_duplicate_email(msg) is True


def test_duplicado_vuelve_a_aceptarse_despues_de_120_segundos(validator, monkeypatch):
    reloj = {"t": 1000.0}
    monkeypatch.setattr("src.email_type.time.time", lambda: reloj["t"])
    msg = mail(message_id="msg-dup")

    validator.is_duplicate_email(msg)
    reloj["t"] += 121
    assert validator.is_duplicate_email(msg) is False


def test_mensajes_distintos_no_son_duplicados(validator):
    assert validator.is_duplicate_email(mail(message_id="msg-a")) is False
    assert validator.is_duplicate_email(mail(message_id="msg-b")) is False


def test_sin_internet_message_id_nunca_es_duplicado(validator):
    msg = mail()
    msg.internet_message_id = None
    assert validator.is_duplicate_email(msg) is False
    assert validator.is_duplicate_email(msg) is False

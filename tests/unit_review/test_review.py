"""review/: aplicación de cambios por hilo y revisión humana.

FakeRepo en memoria que imita la semántica de los SQL (filtro por
``request_code + row_number + status = 'PENDING'``, ``NOT EXISTS`` por serie
en el INSERT). Las decisiones salen del clasificador real con proveedores
falsos (``CLASSIFIER_GATE``/``CLASSIFIER_EXTRACT`` = ``fake``)."""

import asyncio
from types import SimpleNamespace

import pytest

import classifier
import review
from classifier import registry
from classifier.contracts import (
    ACCEPTED,
    AGREGAR,
    AGREGAR_FILAS,
    CANCELAR,
    CANCELAR_FILAS,
    CANCELAR_SOLICITUD,
    CANCELLED,
    COMENTARIO_REVISION,
    ETAPA_REPLY,
    MODIFICAR,
    MODIFICAR_FILAS,
    PENDING,
    Decision,
    FilaRevision,
    GateResult,
    RowExtraida,
    ThreadCtx,
)

RC = "REPARE_000042"


class FakeRepo:
    def __init__(self, filas):
        self.filas = {f["row_number"]: dict(f) for f in filas}
        self.calls = []
        self.request_status = "IN_PROGRESS"

    def _anota(self, fn, *args):
        self.calls.append((fn, args))

    def escrituras(self):
        return [fn for fn, _ in self.calls if fn not in ("email_reply_validate", "get_cooler_rows")]

    def email_reply_validate(self, conversation_id, subject):
        self._anota("email_reply_validate", conversation_id)
        return {"request_code": RC}

    def get_cooler_rows(self, request_code):
        self._anota("get_cooler_rows", request_code)
        return [
            {k: f.get(k) for k in ("row_number", "serie_fabricante", "serie_dnn_bnf", "status")}
            for f in sorted(self.filas.values(), key=lambda f: f["row_number"])
        ]

    def update_pending_cooler_row(self, request_code, row_number, cambios):
        self._anota("update_pending_cooler_row", request_code, row_number, dict(cambios))
        fila = self.filas.get(row_number)
        if request_code != RC or fila is None or fila["status"] != PENDING:
            return []
        for k, v in cambios.items():
            if v is not None and str(v).strip():
                fila[k] = str(v).strip()
        return [{"request_code": request_code, "row_number": row_number}]

    def cancel_pending_cooler_row(self, request_code, row_number):
        self._anota("cancel_pending_cooler_row", request_code, row_number)
        fila = self.filas.get(row_number)
        if request_code != RC or fila is None or fila["status"] != PENDING:
            return []
        fila["status"] = CANCELLED
        return [{"request_code": request_code, "row_number": row_number}]

    def send_email_coolers(self, parametros):
        self._anota("send_email_coolers", parametros["row_number"])
        series = {parametros["serie_fabricante"], parametros["serie_dnn_bnf"]} - {None}
        for f in self.filas.values():
            if f["row_number"] == parametros["row_number"] or series & {f.get("serie_fabricante"), f.get("serie_dnn_bnf")}:
                return []
        self.filas[parametros["row_number"]] = {
            k: parametros[k] for k in ("row_number", "serie_fabricante", "serie_dnn_bnf", "status", "modelo")
        }
        return [{"request_code": RC, "row_number": parametros["row_number"]}]

    def update_email_request(self, request_code):
        self._anota("update_email_request", request_code)
        return [{"request_code": request_code}]

    def cancel_email_request(self, request_code):
        self._anota("cancel_email_request", request_code)
        self.request_status = CANCELLED
        return [{"request_code": request_code}]


def filas_base():
    return [
        {"row_number": 1, "serie_fabricante": "FAB-0001", "serie_dnn_bnf": None, "status": PENDING},
        {"row_number": 2, "serie_fabricante": "FAB-0002", "serie_dnn_bnf": None, "status": PENDING},
        {"row_number": 3, "serie_fabricante": "FAB-0003", "serie_dnn_bnf": "DNN-0003", "status": ACCEPTED},
        {"row_number": 4, "serie_fabricante": "FAB-0004", "serie_dnn_bnf": None, "status": ACCEPTED},
    ]


# ------------------------------------------------------------ proveedor falso
@pytest.fixture
def proveedor(monkeypatch):
    """Proveedor externo falso: lo que devuelve se configura por prueba."""
    salida = SimpleNamespace(
        gate=GateResult(es_os=True, tipo_evento=MODIFICAR_FILAS, confidence=0.95),
        rows=[],
    )
    modulo = SimpleNamespace(
        NAME="fake",
        gate=lambda subject, body, ctx: salida.gate,
        extract=lambda body, ctx: list(salida.rows),
    )
    real_cargar = registry.cargar
    monkeypatch.setattr(registry, "cargar", lambda n: modulo if n == "fake" else real_cargar(n))
    monkeypatch.setattr(registry, "get_redactor", lambda: (lambda t: t))
    monkeypatch.setenv("CLASSIFIER_GATE", "fake")
    monkeypatch.setenv("CLASSIFIER_EXTRACT", "fake")
    return salida


@pytest.fixture
def repo(monkeypatch):
    r = FakeRepo(filas_base())
    monkeypatch.setattr(classifier, "_cargador_contexto", review.cargador(r))
    return r


def correo(adjuntos=False):
    return SimpleNamespace(
        id="msg-1",
        subject="RE: solicitud",
        unique_body=SimpleNamespace(content="texto del cliente"),
        conversation_id="conv-1",
        has_attachments=adjuntos,
    )


def procesar(repo, email=None):
    """Lo que hace src/service.py en el reply: decide, y si toca, atiende."""
    email = email or correo()
    decision, ctx = classifier.decidir_correo(email, "danone", ETAPA_REPLY, "inbound")
    enviados = []

    async def enviar(mensaje):
        enviados.append(mensaje)

    if not review.debe_atender(decision, ctx, email):
        return None, decision, enviados
    out = asyncio.run(review.atender(decision, ctx, repo, enviar))
    return out, decision, enviados


def modificar(rn, **campos):
    return RowExtraida(accion=MODIFICAR, row_number=rn, **campos)


def cancelar(rn):
    return RowExtraida(accion=CANCELAR, row_number=rn)


# ------------------------------------------------------------ PENDING: se aplica
def test_pending_modificada_se_aplica(proveedor, repo):
    proveedor.rows = [modificar(1, modelo="VR-17")]
    out, decision, enviados = procesar(repo)

    assert decision.proveedor_extract == "fake"
    resultado = out["resultado"]
    assert [(f.row_number, f.accion) for f in resultado.aplicadas] == [(1, MODIFICAR)]
    assert resultado.revision == ()
    assert repo.filas[1]["modelo"] == "VR-17"
    assert repo.escrituras() == ["update_pending_cooler_row", "update_email_request"]
    assert enviados == []  # nada a revisión: no se avisa a REPARE
    assert "FAB-0001" in out["mensaje"] and "Aplicado" in out["mensaje"]


def test_pending_cancelada_se_aplica(proveedor, repo):
    proveedor.gate = GateResult(es_os=True, tipo_evento=CANCELAR_FILAS, confidence=0.9)
    proveedor.rows = [cancelar(2)]
    out, _, enviados = procesar(repo)

    assert [(f.row_number, f.accion) for f in out["resultado"].aplicadas] == [(2, CANCELAR)]
    assert repo.filas[2]["status"] == CANCELLED
    assert enviados == []


# ------------------------------------------------------------ ACCEPTED: revisión
def _assert_aviso_repare(mensaje, row_number, serie, accion):
    assert COMENTARIO_REVISION in mensaje
    assert f">{row_number}<" in mensaje
    assert serie in mensaje
    assert accion in mensaje
    assert "fila_accepted" in mensaje


def test_accepted_modificada_va_a_revision(proveedor, repo):
    proveedor.rows = [modificar(3, modelo="OTRO")]
    out, decision, enviados = procesar(repo)

    assert decision.filas_revision == (FilaRevision(3, MODIFICAR, ACCEPTED, "fila_accepted"),)
    resultado = out["resultado"]
    assert resultado.aplicadas == ()
    assert [(f.row_number, f.motivo, f.comentario) for f in resultado.revision] == [
        (3, "fila_accepted", COMENTARIO_REVISION)
    ]
    assert repo.filas[3] == filas_base()[2]  # intacta
    assert repo.escrituras() == []
    assert len(enviados) == 1
    _assert_aviso_repare(enviados[0], 3, "FAB-0003", MODIFICAR)
    assert "En revisión" in out["mensaje"]


def test_accepted_cancelada_va_a_revision(proveedor, repo):
    proveedor.gate = GateResult(es_os=True, tipo_evento=CANCELAR_FILAS, confidence=0.9)
    proveedor.rows = [cancelar(4)]
    out, _, enviados = procesar(repo)

    assert out["resultado"].aplicadas == ()
    assert repo.filas[4]["status"] == ACCEPTED
    assert repo.escrituras() == []
    assert len(enviados) == 1
    _assert_aviso_repare(enviados[0], 4, "FAB-0004", CANCELAR)


def test_mezcla_pending_y_accepted_en_un_correo(proveedor, repo):
    proveedor.gate = GateResult(es_os=True, tipo_evento=CANCELAR_FILAS, confidence=0.9)
    proveedor.rows = [cancelar(1), cancelar(3), cancelar(2), cancelar(4)]
    out, _, enviados = procesar(repo)

    resultado = out["resultado"]
    assert sorted(f.row_number for f in resultado.aplicadas) == [1, 2]
    assert sorted(f.row_number for f in resultado.revision) == [3, 4]
    assert [repo.filas[n]["status"] for n in (1, 2, 3, 4)] == [CANCELLED, CANCELLED, ACCEPTED, ACCEPTED]
    # Solo se tocan las PENDING, una por una, y luego se recalcula la cabecera.
    assert [a for fn, a in repo.calls if fn == "cancel_pending_cooler_row"] == [(RC, 1), (RC, 2)]
    assert repo.escrituras()[-1] == "update_email_request"
    assert len(enviados) == 1
    assert "FAB-0003" in enviados[0] and "FAB-0004" in enviados[0]
    assert "FAB-0001" not in enviados[0]


def test_cancelar_solicitud_con_accepted_no_cancela_la_solicitud(proveedor, repo):
    proveedor.gate = GateResult(es_os=True, tipo_evento=CANCELAR_SOLICITUD, confidence=0.9)
    out, _, enviados = procesar(repo)

    resultado = out["resultado"]
    assert sorted(f.row_number for f in resultado.aplicadas) == [1, 2]
    assert sorted(f.row_number for f in resultado.revision) == [3, 4]
    assert not resultado.solicitud_cancelada
    assert "cancel_email_request" not in repo.escrituras()
    assert len(enviados) == 1


def test_cancelar_solicitud_solo_pending_cancela_la_solicitud(proveedor, monkeypatch):
    r = FakeRepo(filas_base()[:2])
    monkeypatch.setattr(classifier, "_cargador_contexto", review.cargador(r))
    proveedor.gate = GateResult(es_os=True, tipo_evento=CANCELAR_SOLICITUD, confidence=0.9)
    out, _, enviados = procesar(r)

    assert out["resultado"].solicitud_cancelada
    # Recalcula antes de cancelar: update_email_request pondría COMPLETED.
    assert r.escrituras()[-2:] == ["update_email_request", "cancel_email_request"]
    assert enviados == []


# ------------------------------------------------------------ fila inexistente
def test_fila_inexistente_el_clasificador_descarta_y_no_se_atiende(proveedor, repo):
    proveedor.rows = [modificar(1, modelo="VR-17"), modificar(99, modelo="X")]
    out, decision, enviados = procesar(repo)

    # validate rechaza la extracción entera y cae a regex: nada que aplicar.
    assert decision.proveedor_extract == "regex"
    assert any("fila_inexistente" in f for f in decision.fallbacks)
    assert out is None
    assert repo.escrituras() == []
    assert enviados == []


def test_fila_inexistente_en_el_aplicador_va_a_revision():
    r = FakeRepo(filas_base())
    ctx = review.cargador(r)(correo(), ThreadCtx(etapa=ETAPA_REPLY, customer="danone", direccion="inbound"))
    decision = Decision(
        gate=GateResult(True, MODIFICAR_FILAS, 0.9),
        proveedor_gate="fake",
        proveedor_extract="fake",
        rows=(modificar(99, modelo="X"),),
        filas_aplicables=(modificar(99, modelo="X"),),
        filas_revision=(FilaRevision(98, MODIFICAR, None, "estado_no_pending"),),
    )
    resultado = review.aplicar(decision, ctx, r)

    assert resultado.aplicadas == ()
    assert [(f.row_number, f.motivo) for f in resultado.revision] == [
        (98, "fila_inexistente"), (99, "fila_inexistente")
    ]
    assert r.escrituras() == []


# ------------------------------------------------------------ reenvío idéntico
def test_reenvio_identico_no_duplica_ni_reaplica(proveedor, repo):
    proveedor.gate = GateResult(es_os=True, tipo_evento=CANCELAR_FILAS, confidence=0.9)
    proveedor.rows = [cancelar(2), cancelar(3)]

    primero, _, avisos1 = procesar(repo)
    estado = {n: dict(f) for n, f in repo.filas.items()}
    escrituras = len(repo.escrituras())
    segundo, decision2, avisos2 = procesar(repo)

    assert [f.row_number for f in primero["resultado"].aplicadas] == [2]
    # En el reenvío la fila 2 ya está CANCELLED: no se toca y va a revisión
    # (regla: CANCELLED tampoco se toca); la 3 sigue en revisión.
    assert segundo["resultado"].aplicadas == ()
    assert sorted((f.row_number, f.status) for f in decision2.filas_revision) == [(2, CANCELLED), (3, ACCEPTED)]
    assert repo.filas == estado
    assert len(repo.escrituras()) == escrituras
    assert len(avisos1) == len(avisos2) == 1


def test_reenvio_identico_de_alta_no_duplica(proveedor, repo):
    proveedor.gate = GateResult(es_os=True, tipo_evento=AGREGAR_FILAS, confidence=0.9)
    proveedor.rows = [RowExtraida(accion=AGREGAR, serie_fabricante="FAB-0009", modelo="VR-17")]

    primero, _, _ = procesar(repo)
    segundo, _, avisos = procesar(repo)

    assert [(f.row_number, f.serie) for f in primero["resultado"].aplicadas] == [(5, "FAB-0009")]
    assert segundo["resultado"].aplicadas == ()
    assert [f.motivo for f in segundo["resultado"].sin_cambios] == ["serie_ya_registrada"]
    assert len(repo.filas) == 5
    assert avisos == []
    assert "Sin cambios" in segundo["mensaje"]


def test_reenvio_identico_de_modificacion_es_idempotente(proveedor, repo):
    proveedor.rows = [modificar(1, modelo="VR-17")]
    procesar(repo)
    estado = {n: dict(f) for n, f in repo.filas.items()}
    out, _, _ = procesar(repo)

    assert [f.row_number for f in out["resultado"].aplicadas] == [1]
    assert repo.filas == estado


def test_agregar_sin_serie_va_a_revision(proveedor, repo):
    proveedor.gate = GateResult(es_os=True, tipo_evento=AGREGAR_FILAS, confidence=0.9)
    proveedor.rows = [RowExtraida(accion=AGREGAR, modelo="VR-17")]
    out, _, enviados = procesar(repo)

    assert [f.motivo for f in out["resultado"].revision] == ["agregar_sin_serie"]
    assert "send_email_coolers" not in repo.escrituras()
    assert len(enviados) == 1


# ------------------------------------------------------------ carreras y errores
def test_fila_que_deja_de_ser_pending_antes_del_update_va_a_revision(proveedor, repo):
    proveedor.rows = [modificar(1, modelo="VR-17")]
    real = repo.get_cooler_rows

    def cargar_y_aceptar(request_code):
        filas = real(request_code)
        repo.filas[1]["status"] = ACCEPTED  # outbound entre la carga y el UPDATE
        return filas

    repo.get_cooler_rows = cargar_y_aceptar
    out, _, enviados = procesar(repo)

    assert out["resultado"].aplicadas == ()
    assert [(f.row_number, f.motivo) for f in out["resultado"].revision] == [(1, "estado_cambio")]
    assert repo.filas[1].get("modelo") is None
    assert len(enviados) == 1


def test_error_de_repositorio_va_a_revision_y_aviso_fallido_no_corta(proveedor, repo):
    proveedor.rows = [modificar(1, modelo="VR-17")]

    def falla(*a):
        raise RuntimeError("db caída")

    repo.update_pending_cooler_row = falla
    email = correo()
    decision, ctx = classifier.decidir_correo(email, "danone", ETAPA_REPLY, "inbound")

    async def enviar(_):
        raise RuntimeError("graph caído")

    out = asyncio.run(review.atender(decision, ctx, repo, enviar))
    assert [(f.row_number, f.motivo) for f in out["resultado"].revision] == [(1, "error_repositorio")]
    assert out["resultado"].errores == ("modificar:1:RuntimeError",)
    assert "requiere revisión" in out["mensaje"]


# ------------------------------------------------------------ cuándo se activa
def test_con_extract_regex_no_se_atiende(proveedor, repo, monkeypatch):
    proveedor.rows = [modificar(1, modelo="VR-17")]
    monkeypatch.setenv("CLASSIFIER_EXTRACT", "regex")
    out, decision, _ = procesar(repo)
    assert out is None
    assert decision.rows == ()
    assert repo.escrituras() == []


def test_default_sin_variables_no_carga_contexto_ni_atiende(repo, monkeypatch):
    monkeypatch.delenv("CLASSIFIER_GATE", raising=False)
    monkeypatch.delenv("CLASSIFIER_EXTRACT", raising=False)
    out, decision, _ = procesar(repo)
    assert out is None
    assert repo.calls == []  # con regex ni siquiera se consulta el hilo


def test_con_excel_manda_el_parser(proveedor, repo):
    proveedor.rows = [modificar(1, modelo="VR-17")]
    out, _, _ = procesar(repo, correo(adjuntos=True))
    assert out is None
    assert repo.escrituras() == []


@pytest.mark.parametrize("direccion", ["outbound", "reply_to_bot", "bot"])
def test_solo_inbound(proveedor, repo, direccion):
    proveedor.rows = [modificar(1, modelo="VR-17")]
    email = correo()
    decision, ctx = classifier.decidir_correo(email, "danone", ETAPA_REPLY, direccion)
    assert not review.debe_atender(decision, ctx, email)


# ------------------------------------------------------------ cargador
def test_cargador_sin_pii_y_solo_en_reply():
    r = FakeRepo(filas_base())
    cargar = review.cargador(r)
    ctx = cargar(correo(), ThreadCtx(etapa=ETAPA_REPLY))
    assert ctx.request_code == RC
    assert [(f.row_number, f.status) for f in ctx.filas] == [(1, PENDING), (2, PENDING), (3, ACCEPTED), (4, ACCEPTED)]
    assert ctx.fila(3).serie_dnn_bnf == "DNN-0003"

    r.calls.clear()
    init = ThreadCtx(etapa="init")
    assert cargar(correo(), init) is init
    assert r.calls == []


def test_cargador_sin_solicitud_deja_filas_sin_cargar():
    r = FakeRepo(filas_base())
    r.email_reply_validate = lambda *a: None
    ctx = review.cargador(r)(correo(), ThreadCtx(etapa=ETAPA_REPLY))
    assert ctx.request_code is None and ctx.filas is None


# ------------------------------------------------------------ service.py
def test_service_registra_el_cargador_y_entrega_la_decision(monkeypatch):
    import src.service as service

    assert classifier._cargador_contexto is not None
    permite, decision, ctx = service.classifier_evaluar(correo(), "danone", ETAPA_REPLY, "inbound")
    assert permite is True
    assert isinstance(decision, Decision) and isinstance(ctx, ThreadCtx)
    assert service.classifier_permite(correo(), "danone", ETAPA_REPLY, "inbound") is True

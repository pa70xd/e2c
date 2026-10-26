"""Backfill: solo lectura, redacción antes de escribir, etiquetado y split.

Graph y PostgreSQL son falsos y los datos están inventados (``example.com``).
Nada de esto es una corrida real: sirve para probar la lógica del script.
"""

import base64
import datetime as dt
import glob
import io
import json
import os
import pathlib
import re
from types import SimpleNamespace

import openpyxl
import pytest

from eval import backfill, run_eval

REPO = pathlib.Path(__file__).resolve().parents[2]
HOY = dt.date(2026, 10, 26)
BUZON = "cliente.danone@repare.com.mx"
CLIENTE = "danone"
CORREO_RAW = "juan.perez@example.com"
TEL_RAW = "55 1234 5678"


def d(texto):
    return dt.datetime.fromisoformat(texto)


# ------------------------------------------------------------------ Graph falso
class FakeHttp:
    """Solo existe ``get``. Cualquier otro método de escritura revienta."""

    def __init__(self, mensajes, adjuntos):
        self.mensajes = mensajes
        self.adjuntos = adjuntos
        self.llamadas = []

    def get(self, url, headers=None, params=None, timeout=None):
        self.llamadas.append(("GET", url))
        ruta = url.split("/v1.0", 1)[1]
        if m := re.fullmatch(r"/users/([^/]+)/messages", ruta):
            filtro = params["$filter"]
            ge, lt = re.search(r"ge (\S+) and receivedDateTime lt (\S+) ", filtro).groups()
            lista = [
                x for x in self.mensajes
                if x["_buzon"] == m.group(1) and ge <= x["receivedDateTime"] < lt
            ]
            lista.sort(key=lambda x: x["receivedDateTime"], reverse=True)
            return self._resp({"value": [{k: v for k, v in x.items() if k != "_buzon"} for x in lista[: int(params["$top"])]]})
        if m := re.fullmatch(r"/users/[^/]+/messages/([^/]+)/attachments", ruta):
            return self._resp({"value": [
                {k: v for k, v in a.items() if k != "contentBytes"} for a in self.adjuntos.get(m.group(1), [])
            ]})
        if m := re.fullmatch(r"/users/[^/]+/messages/([^/]+)/attachments/([^/]+)", ruta):
            return self._resp(next(a for a in self.adjuntos[m.group(1)] if a["id"] == m.group(2)))
        raise AssertionError(f"GET inesperado {ruta}")

    @staticmethod
    def _resp(datos):
        return SimpleNamespace(status_code=200, headers={}, json=lambda: datos, raise_for_status=lambda: None)

    def post(self, *a, **k):
        raise AssertionError("POST a Graph")

    patch = put = delete = request = post


def xlsx_b64():
    libro = openpyxl.Workbook()
    hoja = libro.active
    hoja.title = "Solicitudes"
    hoja.append(["Serie", "Modelo", f"Contacto {CORREO_RAW}"])
    hoja.append(["SF-1001", "VR-26", "x"])
    hoja.append(["SF-1002", "VR-26", "y"])
    libro.create_sheet("Notas").append(["Nota"])
    buf = io.BytesIO()
    libro.save(buf)
    return base64.b64encode(buf.getvalue()).decode()


def graph_msg(n, recibido, asunto, cuerpo="Sin datos", de="ana@example.com", para=BUZON, adjuntos=False, conv="C1"):
    return {
        "_buzon": BUZON, "id": f"AAMk-m{n}", "internetMessageId": f"<m{n}@example.com>",
        "conversationId": conv, "subject": asunto,
        "from": {"emailAddress": {"address": de}},
        "toRecipients": [{"emailAddress": {"address": para}}],
        "receivedDateTime": recibido, "hasAttachments": adjuntos,
        "uniqueBody": {"content": cuerpo},
    }


def mensajes_graph():
    cuerpo1 = f"Favor de dar servicio a SF-1001 y SF-1002. Contacto: Juan Pérez {TEL_RAW} {CORREO_RAW}\n\nSaludos,\nJuan Pérez\nTel {TEL_RAW}"
    return [
        graph_msg(1, "2026-09-01T15:00:00Z", f"Solicitud {CORREO_RAW}", cuerpo1, adjuntos=True),
        graph_msg(2, "2026-09-02T15:00:00Z", "Re: Solicitud", "Agreguen la serie SF-3003"),
        graph_msg(3, "2026-09-03T15:00:00Z", "Re: Solicitud", "Cancelen la primera"),
        graph_msg(4, "2026-10-10T15:00:00Z", "Re: Solicitud", "Gracias"),
        graph_msg(5, "2026-10-12T15:00:00Z", "Re: Solicitud", "Sin registro en la base"),
        graph_msg(6, "2026-10-15T15:00:00Z", "Cierre", "Adjunto OS", de=BUZON, para="cliente@example.com", adjuntos=True),
        graph_msg(7, "2026-10-16T15:00:00Z", "Resumen", "Estimado usuario REPARE, estatus", de=BUZON, para=BUZON, conv="C3"),
        graph_msg(8, "2026-10-17T15:00:00Z", "Hola", "No se pudo leer", conv="C2"),
    ]


def adjuntos_graph():
    return {
        "AAMk-m1": [{"id": "a1", "name": "solicitud_juan.xlsx", "contentType": "application/vnd.ms-excel",
                     "size": 5000, "contentBytes": xlsx_b64()}],
        "AAMk-m6": [{"id": "a6", "name": "OS.pdf", "contentType": "application/pdf", "size": 100}],
    }


# ------------------------------------------------------------------ PostgreSQL falso
def log(n, conv, codigo, creado, direccion="inbound", estado="OK"):
    return {"id": n, "graph_message_id": f"AAMk-m{n}", "internet_message_id": f"<m{n}@example.com>",
            "conversation_id": conv, "request_code": codigo, "direction": direccion,
            "processing_status": estado, "customer": CLIENTE, "created_at": d(creado)}


def datos_db(desfase=dt.timedelta(0)):
    """``desfase``: cooler_request guarda otro huso que emails_log."""
    def t(x):
        return d(x) + desfase

    return {
        "logs": [
            log(1, "C1", "R1", "2026-09-01T15:00:01"),
            log(2, "C1", "R1", "2026-09-02T15:00:01"),
            log(3, "C1", "R1", "2026-09-03T15:00:01"),
            log(4, "C1", "R1", "2026-10-10T15:00:01"),
            log(6, "C1", "R1", "2026-10-15T15:00:01", direccion="outbound"),
            log(8, "C2", None, "2026-10-17T15:00:01", estado="ERROR"),
        ],
        "solicitudes": [{"request_code": "R1", "customer": CLIENTE, "status": "IN_PROGRESS", "total_coolers": 3,
                         "pending_coolers": 2, "completed_coolers": 0, "failed_coolers": 0, "created_at": t("2026-09-01T15:00:05")}],
        "coolers": [
            {"request_code": "R1", "row_number": 1, "serie_fabricante": "SF-1001", "serie_dnn_bnf": None, "os": None,
             "status": "CANCELLED", "created_at": t("2026-09-01T15:00:06"), "updated_at": t("2026-09-03T15:00:03")},
            {"request_code": "R1", "row_number": 2, "serie_fabricante": "SF-1002", "serie_dnn_bnf": None, "os": "OS-777",
             "status": "PENDING", "created_at": t("2026-09-01T15:00:06"), "updated_at": t("2026-09-01T15:00:06")},
            {"request_code": "R1", "row_number": 3, "serie_fabricante": "SF-3003", "serie_dnn_bnf": None, "os": None,
             "status": "PENDING", "created_at": t("2026-09-02T15:00:05"), "updated_at": t("2026-09-02T15:00:05")},
        ],
    }


class FakeCursor:
    def __init__(self, conn):
        self.conn = conn
        self._rows = []

    def execute(self, sql, params=()):
        self.conn.sentencias.append(sql)
        s = sql.upper()
        if s.startswith("SET TRANSACTION"):
            self._rows = []
        elif "FROM REPARE_EMAIL_PARSE.EMAILS_LOG" in s and "GRAPH_MESSAGE_ID = ANY" in s:
            ids = set(params[0]) | set(params[1])
            self._rows = [r for r in self.conn.datos["logs"] if r["graph_message_id"] in ids or r["internet_message_id"] in ids]
        elif "FROM REPARE_EMAIL_PARSE.EMAILS_LOG" in s:
            self._rows = [r for r in self.conn.datos["logs"] if r["conversation_id"] in set(params[0])]
        elif "EMAIL_REQUEST" in s:
            self._rows = [r for r in self.conn.datos["solicitudes"] if r["request_code"] in set(params[0])]
        elif "COOLER_REQUEST" in s:
            self._rows = [r for r in self.conn.datos["coolers"] if r["request_code"] in set(params[0])]
        else:
            raise AssertionError(f"sentencia desconocida: {sql[:40]}")

    def fetchall(self):
        return self._rows


class FakeConn:
    def __init__(self, datos):
        self.datos = datos
        self.sentencias = []
        self.commits = 0
        self.rollbacks = 0
        self.cerrada = False

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.cerrada = True


class Entorno:
    def __init__(self, tmp_path, datos=None):
        self.http = FakeHttp(mensajes_graph(), adjuntos_graph())
        self.conn = FakeConn(datos or datos_db())
        self.salida = str(tmp_path / "out" / "backfill.jsonl")

    def correr(self, *extra):
        graph = backfill.LectorGraph(lambda: "token-falso", http_get=self.http.get, dormir=lambda s: None)
        return backfill.main(
            ["--buzones", BUZON, "--salida", self.salida, *extra],
            graph=graph, abrir_pg=lambda: self.conn, hoy=HOY,
        )

    def casos(self, ruta=None):
        with open(ruta or self.salida, encoding="utf-8") as fh:
            return {c["ids"]["mensaje"]: c for c in map(json.loads, fh)}

    def caso(self, n):
        return self.casos()[backfill.hash_id(f"AAMk-m{n}")]


@pytest.fixture(autouse=True)
def _redact_v2(monkeypatch):
    """Por defecto simula un redact v2; los tests del candado lo cambian."""
    monkeypatch.setattr(backfill._modulo_redact, "REDACT_VERSION", 2, raising=False)


@pytest.fixture
def entorno(tmp_path):
    return Entorno(tmp_path)


def test_aborta_con_redact_v1_sin_tocar_graph_ni_base(entorno, monkeypatch, capsys):
    monkeypatch.delattr(backfill._modulo_redact, "REDACT_VERSION")
    assert entorno.correr() == 5
    assert "REDACT" in capsys.readouterr().err.upper()
    assert entorno.http.llamadas == [] and entorno.conn.sentencias == []
    assert not os.path.exists(entorno.salida)


def test_redact_version_1_explicita_tambien_aborta(entorno, monkeypatch):
    monkeypatch.setattr(backfill._modulo_redact, "REDACT_VERSION", 1)
    assert entorno.correr() == 5


def test_permitir_redact_v1_deja_correr(entorno, monkeypatch):
    monkeypatch.delattr(backfill._modulo_redact, "REDACT_VERSION")
    assert entorno.correr("--permitir-redact-v1") == 0
    assert os.path.exists(entorno.salida)


# ------------------------------------------------------------------ solo lectura: SQL
@pytest.mark.parametrize("sql", [
    "SELECT 1",
    "select a, updated_at, created_at from t where x = ANY(%s);",
    "-- comentario con UPDATE\nSELECT 'DELETE; DROP' AS txt FROM t",
    "SELECT a FROM t /* INSERT */",
])
def test_validar_select_acepta_selects(sql):
    assert backfill.validar_select(sql) == sql


@pytest.mark.parametrize("sql", [
    "INSERT INTO t VALUES (1)",
    "UPDATE t SET a = 1",
    "DELETE FROM t",
    "WITH x AS (DELETE FROM t RETURNING *) SELECT * FROM x",
    "WITH x AS (SELECT 1) SELECT * FROM x",
    "SELECT 1; DROP TABLE t",
    "SELECT * INTO nueva FROM t",
    "SELECT * FROM t FOR UPDATE",
    "TRUNCATE t",
    "",
    "SELECT set_config('x', 'y', false)",
])
def test_validar_select_rechaza_lo_que_no_es_select(sql):
    with pytest.raises(backfill.ConsultaNoPermitida):
        backfill.validar_select(sql)


@pytest.mark.parametrize("ruta", sorted(glob.glob(str(REPO / "eval" / "querys" / "*.sql"))))
def test_todas_las_consultas_del_repo_son_select(ruta):
    for tablas in backfill.TABLAS.values():
        backfill.validar_select(open(ruta, encoding="utf-8").read().format(**tablas))


def test_consultas_solo_piden_las_tablas_permitidas():
    for ruta in glob.glob(str(REPO / "eval" / "querys" / "*.sql")):
        sql = open(ruta, encoding="utf-8").read()
        assert set(re.findall(r"\{(\w+)\}", sql)) <= set(backfill.TABLAS["qa"])


def test_lector_pg_abre_read_only_y_nunca_hace_commit(entorno):
    pg = backfill.LectorPG(entorno.conn, backfill.TABLAS["qa"])
    pg.consultar("solicitudes", ["R1"])
    pg.cerrar()
    assert entorno.conn.sentencias[0] == "SET TRANSACTION READ ONLY"
    assert all(backfill.validar_select(s) for s in entorno.conn.sentencias[1:])
    assert entorno.conn.commits == 0 and entorno.conn.rollbacks == 1 and entorno.conn.cerrada


def test_sql_que_no_es_select_aborta_antes_de_ejecutar(tmp_path, entorno, monkeypatch, capsys):
    (tmp_path / "q").mkdir()
    for nombre in ("logs_por_mensaje", "logs_por_conversacion", "solicitudes", "coolers"):
        (tmp_path / "q" / f"{nombre}.sql").write_text("SELECT 1 FROM {emails_log_table}")
    (tmp_path / "q" / "logs_por_mensaje.sql").write_text(
        "UPDATE {emails_log_table} SET processing_status = 'X' WHERE graph_message_id = ANY(%s)"
    )
    monkeypatch.setattr(backfill, "QUERYS_DIR", str(tmp_path / "q"))
    assert entorno.correr() == 3
    assert "ABORTADO" in capsys.readouterr().err
    assert not any("UPDATE" in s.upper() for s in entorno.conn.sentencias)
    assert entorno.conn.commits == 0 and entorno.conn.cerrada
    assert not os.path.exists(entorno.salida)


def test_prod_exige_confirmacion(entorno, capsys):
    assert entorno.correr("--tablas", "prod") == 2
    assert "--confirmo-solo-lectura" in capsys.readouterr().err
    assert entorno.conn.sentencias == []


def test_tablas_qa_y_prod_apuntan_a_las_tablas_correctas(entorno):
    assert entorno.correr() == 0
    assert any("emails_log_qa" in s for s in entorno.conn.sentencias)
    assert not any("cooler_request " in s and "_qa" not in s for s in entorno.conn.sentencias if "FROM" in s.upper())
    otro = Entorno(pathlib.Path(entorno.salida).parent.parent / "p")
    assert otro.correr("--tablas", "prod", "--confirmo-solo-lectura") == 0
    assert any("repare_email_parse.emails_log" in s and "_qa" not in s for s in otro.conn.sentencias)
    assert not any("_qa" in s for s in otro.conn.sentencias)


# ------------------------------------------------------------------ solo lectura: Graph
def test_graph_solo_hace_get(entorno):
    assert entorno.correr() == 0
    assert entorno.http.llamadas and {m for m, _ in entorno.http.llamadas} == {"GET"}
    assert all(u.startswith("https://graph.microsoft.com/v1.0/users/") for _, u in entorno.http.llamadas)
    assert not any("/send" in u or "/reply" in u or "/move" in u for _, u in entorno.http.llamadas)


def test_lector_graph_no_tiene_metodos_de_escritura_ni_urls_ajenas():
    assert not any(hasattr(backfill.LectorGraph, n) for n in ("post", "patch", "put", "delete", "send", "reply", "move"))
    lector = backfill.LectorGraph(lambda: "t", http_get=lambda *a, **k: pytest.fail("no debe salir"))
    with pytest.raises(backfill.LecturaNoPermitida):
        lector.get("https://example.com/v1.0/users/x/messages")


def test_codigo_no_contiene_escrituras_ni_el_flujo_de_produccion():
    fuente = (REPO / "eval" / "backfill.py").read_text(encoding="utf-8")
    prohibido = [
        r"\.(post|patch|put|delete)\(", r"requests\.(post|patch|put|delete|request)",
        r"processMail", r"reply_mail", r"sendMail", r"send_mail",
        r"^\s*(from|import)\s+(parsers|review|src|repository|bot)\b",
        r"execute_query", r"\.commit\(",
    ]
    for patron in prohibido:
        assert not re.search(patron, fuente, re.M), patron


def test_reintenta_429_solo_con_get():
    llamadas = []

    def http_get(url, headers=None, params=None, timeout=None):
        llamadas.append(url)
        if len(llamadas) == 1:
            return SimpleNamespace(status_code=429, headers={"Retry-After": "1"}, json=lambda: {}, raise_for_status=lambda: None)
        return SimpleNamespace(status_code=200, headers={}, json=lambda: {"ok": 1}, raise_for_status=lambda: None)

    esperas = []
    lector = backfill.LectorGraph(lambda: "t", http_get=http_get, dormir=esperas.append)
    assert lector.get("/users/x/messages") == {"ok": 1}
    assert esperas == [1.0] and len(llamadas) == 2


# ------------------------------------------------------------------ privacidad
def test_nada_sin_redactar_toca_el_disco(entorno):
    assert entorno.correr() == 0
    for ruta in (entorno.salida, backfill.ruta_revision(entorno.salida)):
        texto = open(ruta, encoding="utf-8").read()
        assert CORREO_RAW not in texto and TEL_RAW not in texto
        assert "contentBytes" not in texto and "AAMk" not in texto
    c1 = entorno.caso(1)
    assert "[CORREO]" in c1["cuerpo"] and "[TELEFONO]" in c1["cuerpo"]
    assert "[CORREO]" in c1["asunto"]


def test_asunto_cuerpo_y_adjuntos_pasan_por_redact_antes_de_escribir(entorno, monkeypatch):
    llamadas = []

    def espia(texto, conservar=()):
        llamadas.append(texto)
        return "[R]"

    monkeypatch.setattr(backfill, "redact", espia)
    escritos = []
    original = backfill.escribir_jsonl
    monkeypatch.setattr(backfill, "escribir_jsonl", lambda ruta, casos: (escritos.append(len(llamadas)), original(ruta, casos)))
    assert entorno.correr() == 0
    assert escritos and all(n > 0 for n in escritos)
    for caso in entorno.casos().values():
        assert caso["asunto"] == "[R]" and caso["cuerpo"] in ("[R]", "")
        for adj in caso["adjuntos"]:
            assert adj["nombre"] == "[R]"
    texto = open(entorno.salida, encoding="utf-8").read()
    assert "Favor de dar servicio" not in texto and "solicitud_juan" not in texto


def test_ids_se_guardan_como_hash(entorno):
    assert entorno.correr() == 0
    texto = open(entorno.salida, encoding="utf-8").read()
    for crudo in ("AAMk-m1", "<m1@example.com>", "C1", "R1"):
        assert f'"{crudo}"' not in texto
    c1 = entorno.caso(1)
    assert c1["ids"] == {"mensaje": backfill.hash_id("AAMk-m1"), "hilo": backfill.hash_id("C1"), "solicitud": backfill.hash_id("R1")}
    assert c1["id"] == "bf-" + backfill.hash_id("AAMk-m1")
    assert backfill.main(["--hash", "AAMk-m1"]) == 0


def test_adjuntos_solo_resumen(entorno):
    assert entorno.correr() == 0
    adj = entorno.caso(1)["adjuntos"][0]
    assert set(adj) == {"nombre", "tipo", "hojas", "filas", "detalle_hojas"}
    assert adj["hojas"] == 2 and adj["filas"] == 2
    primera = adj["detalle_hojas"][0]
    assert primera["encabezados"][:2] == ["Serie", "Modelo"] and primera["encabezados"][2] == "Contacto [CORREO]"
    assert entorno.caso(6)["adjuntos"] == [{"nombre": "OS.pdf", "tipo": "application/pdf"}]


# ------------------------------------------------------------------ etiquetado
def test_etiquetas_por_correo(entorno):
    assert entorno.correr() == 0
    c1 = entorno.caso(1)
    assert c1["etapa"] == "init" and c1["etiqueta_fuente"] == "historico"
    assert c1["esperado"]["es_os"] is True and c1["esperado"]["tipo_evento"] == "nueva_solicitud"
    assert c1["evidencia"]["filas_generadas"] == 2
    assert c1["evidencia"]["estados"] == {"CANCELLED": 1, "PENDING": 1}
    assert c1["evidencia"]["filas_con_os"] == 1

    c2 = entorno.caso(2)
    assert c2["etapa"] == "reply" and c2["esperado"]["tipo_evento"] == "agregar_filas"
    assert c2["esperado"]["filas"] == [{"accion": "agregar", "row_number": None, "serie_fabricante": "SF-3003"}]
    assert [f["row_number"] for f in c2["thread_ctx"]["filas"]] == [1, 2] and c2["ctx_aproximado"]

    c3 = entorno.caso(3)
    assert c3["esperado"]["tipo_evento"] == "cancelar_filas"
    assert c3["esperado"]["filas"] == [{"accion": "cancelar", "row_number": 1}]
    ctx3 = {f["row_number"]: f["status"] for f in c3["thread_ctx"]["filas"]}
    assert ctx3 == {1: "PENDING", 2: "PENDING", 3: "PENDING"}

    c6 = entorno.caso(6)
    assert c6["categoria"] == "cierre" and c6["etiqueta_fuente"] == "historico"
    assert c6["esperado"]["es_os"] is True and c6["esperado"]["tipo_evento"] is None


def test_sin_rastro_es_null_y_nunca_no_os(entorno):
    assert entorno.correr() == 0
    casos = entorno.casos()
    for n in (4, 5, 8):
        c = casos[backfill.hash_id(f"AAMk-m{n}")]
        assert c["etiqueta_fuente"] == "sin_evidencia"
        assert c["esperado"]["es_os"] is None and c["esperado"]["tipo_evento"] is None
    assert entorno.caso(5)["evidencia"]["motivo"] == "hilo_con_rastro_mensaje_sin_log"
    assert entorno.caso(8)["evidencia"]["procesamiento"] == "ERROR"
    assert entorno.caso(4)["evidencia"]["motivo"] == "sin_cambios_en_la_ventana"
    for c in casos.values():
        assert c["esperado"]["es_os"] is not False
        assert c["esperado"]["tipo_evento"] not in ("no_os", "duplicado")


def test_sin_evidencia_sale_en_archivo_aparte(entorno):
    assert entorno.correr() == 0
    revision = entorno.casos(backfill.ruta_revision(entorno.salida))
    assert set(revision) == {backfill.hash_id(f"AAMk-m{n}") for n in (4, 5, 6, 8)}
    assert all(c["esperado"]["tipo_evento"] is None for c in revision.values())


def test_mensajes_del_bot_se_omiten(entorno, capsys):
    assert entorno.correr() == 0
    assert backfill.hash_id("AAMk-m7") not in entorno.casos()
    assert "bot omitidos 1" in capsys.readouterr().out


def test_reloj_distinto_en_cooler_request_se_calibra(tmp_path):
    entorno = Entorno(tmp_path, datos_db(desfase=-dt.timedelta(hours=6)))
    assert entorno.correr() == 0
    assert entorno.caso(2)["esperado"]["tipo_evento"] == "agregar_filas"
    assert entorno.caso(3)["esperado"]["tipo_evento"] == "cancelar_filas"


def test_sin_calibracion_no_se_inventa_evento(tmp_path):
    datos = datos_db()
    datos["logs"] = [r for r in datos["logs"] if r["graph_message_id"] != "AAMk-m1"]
    entorno = Entorno(tmp_path, datos)
    assert entorno.correr() == 0
    c2 = entorno.caso(2)
    assert c2["esperado"]["tipo_evento"] is None and c2["etiqueta_fuente"] == "sin_evidencia"


def test_eventos_mezclados_no_eligen_tipo(tmp_path):
    datos = datos_db()
    datos["coolers"][1]["updated_at"] = d("2026-09-03T15:00:04")  # modificar la fila 2 en la misma ventana
    entorno = Entorno(tmp_path, datos)
    assert entorno.correr() == 0
    c3 = entorno.caso(3)
    assert c3["esperado"]["es_os"] is True and c3["esperado"]["tipo_evento"] is None
    assert c3["evidencia"]["motivo"] == "eventos_mezclados" and c3["etiqueta_fuente"] == "sin_evidencia"


def test_solicitud_sin_filas_es_sin_evidencia(tmp_path):
    datos = datos_db()
    datos["logs"].append(log(9, "C9", "R9", "2026-10-18T10:00:00"))
    datos["solicitudes"].append({"request_code": "R9", "customer": CLIENTE, "status": "IN_PROGRESS", "total_coolers": 0,
                                 "pending_coolers": 0, "completed_coolers": 0, "failed_coolers": 0, "created_at": d("2026-10-18T10:00:00")})
    entorno = Entorno(tmp_path, datos)
    entorno.http.mensajes.append(graph_msg(9, "2026-10-18T10:00:00Z", "Solicitud", conv="C9"))
    assert entorno.correr() == 0
    c9 = entorno.caso(9)
    assert c9["esperado"]["es_os"] is None and c9["evidencia"]["motivo"] == "solicitud_sin_filas"


# ------------------------------------------------------------------ split
def test_split_por_corte_por_defecto_ultimos_30_dias(entorno):
    assert entorno.correr() == 0
    por_split = {n: entorno.caso(n)["split"] for n in (1, 2, 3, 4, 5, 6, 8)}
    assert por_split == {1: "ajuste", 2: "ajuste", 3: "ajuste", 4: "examen", 5: "examen", 6: "examen", 8: "examen"}


def test_split_con_corte_explicito(entorno):
    assert entorno.correr("--corte", "2026-09-03") == 0
    assert [entorno.caso(n)["split"] for n in (1, 2, 3)] == ["ajuste", "ajuste", "examen"]


def test_rangos_reparten_el_cupo():
    desde, hasta, corte = dt.datetime(2026, 7, 1), dt.datetime(2026, 10, 1), dt.datetime(2026, 9, 1)
    assert backfill.calcular_rangos(desde, hasta, corte, 101) == [(desde, corte, 50, "ajuste"), (corte, hasta, 51, "examen")]
    assert backfill.calcular_rangos(desde, hasta, hasta, 10) == [(desde, hasta, 10, "ajuste")]
    assert backfill.calcular_rangos(desde, hasta, desde, 10) == [(desde, hasta, 10, "examen")]
    with pytest.raises(ValueError):
        backfill.calcular_rangos(hasta, desde, corte, 10)


def test_maximo_por_buzon(entorno):
    assert entorno.correr("--maximo", "2") == 0
    assert len(entorno.casos()) <= 2


def test_salida_por_defecto_va_a_sets_real():
    args = backfill.parsear([], HOY)
    assert args.salida == os.path.join(backfill.SALIDA_DIR, "backfill_2026-10-26.jsonl")
    assert args.salida.startswith(str(REPO / "eval" / "sets" / "real"))
    assert args.tablas == "qa" and args.maximo == 100


# ------------------------------------------------------------------ compatibilidad con run_eval
def test_salida_compatible_con_run_eval(entorno, capsys):
    assert entorno.correr() == 0
    with pytest.raises(run_eval.SetInvalido, match="--solo-etiquetados"):
        run_eval.cargar_set(entorno.salida)
    omitidos = {}
    casos = run_eval.cargar_set(entorno.salida, solo_etiquetados=True, omitidos=omitidos)
    assert {c["id"] for c in casos} == {"bf-" + backfill.hash_id(f"AAMk-m{n}") for n in (1, 2, 3)}
    assert omitidos == {"sin_etiqueta": 4}
    ajuste = run_eval.cargar_set(entorno.salida, solo_etiquetados=True, split="ajuste")
    assert len(ajuste) == 3
    with pytest.raises(run_eval.SetInvalido):
        run_eval.cargar_set(entorno.salida, solo_etiquetados=True, split="examen")
    capsys.readouterr()
    codigo = run_eval.main(["--provider", "regex", "--set", entorno.salida, "--solo-etiquetados", "--split", "ajuste", "--umbral", "0.0"])
    salida = capsys.readouterr().out
    assert codigo == 0 and "casos=3" in salida and "Casos omitidos" in salida
    assert run_eval.main(["--provider", "regex", "--set", entorno.salida]) == 2

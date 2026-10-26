"""Backfill del set de evaluación real, SOLO LECTURA.

    python eval/backfill.py --tablas qa --desde 2026-07-01 --hasta 2026-10-26

Lee correos históricos de los buzones (Graph, solo consultas GET) y cruza cada
uno con ``emails_log``, ``email_request`` y ``cooler_request`` (PostgreSQL, solo
SELECT en una transacción READ ONLY) para etiquetar sin trabajo manual:
si un correo generó filas en la base, era una OS y se procesó bien.

Usa las variables de entorno que ya existen (Graph: CLIENT_ID, CLIENT_SECRET,
TENANT_ID; PostgreSQL: SECRET_PG_ACC, DB_HOST, DB_NAME, DB_PORT). No procesa
correos, no llama a parsers ni a ``review/``: no escribe en la base ni en los
buzones.

Etiquetas (``etiqueta_fuente``):

* ``historico``: la base prueba el resultado (filas generadas, cambios de filas
  dentro de la ventana del correo, o un cierre con OS adjuntas).
* ``sin_evidencia``: no hay rastro suficiente. ``es_os`` queda en null: NUNCA se
  asume ``no_os``, porque un correo pudo ser una OS y fallar al parsear. Estos
  casos también salen en ``<salida>_revision.jsonl`` para revisión humana.

Privacidad: asunto, cuerpo, nombres de adjuntos y encabezados pasan por
``classifier.redact.redact`` antes de escribirse; los ids se guardan como hash;
los adjuntos no se guardan (solo nombre, tipo, hojas, filas y encabezados).

Código de salida: 0 ok; 2 argumentos o confirmación faltante; 3 aborto por
consulta no permitida o lectura no permitida; 4 fallo de Graph o de la base.
"""

from __future__ import annotations

import argparse
import base64
import collections
import datetime as dt
import hashlib
import io
import json
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from classifier.redact import redact  # noqa: E402

QUERYS_DIR = os.path.join(ROOT, "eval", "querys")
EMAIL_INDEX = os.path.join(ROOT, "config", "email_index.json")
SALIDA_DIR = os.path.join(ROOT, "eval", "sets", "real")

GRAPH_URL = "https://graph.microsoft.com/v1.0"
DB_SCHEMA = "repare_email_parse"
TABLAS = {
    "qa": {
        "emails_log_table": f"{DB_SCHEMA}.emails_log_qa",
        "email_request_table": f"{DB_SCHEMA}.email_request_qa",
        "cooler_request_table": f"{DB_SCHEMA}.cooler_request_qa",
    },
    "prod": {
        "emails_log_table": f"{DB_SCHEMA}.emails_log",
        "email_request_table": f"{DB_SCHEMA}.email_request",
        "cooler_request_table": f"{DB_SCHEMA}.cooler_request",
    },
}

MAX_POR_BUZON = 100
DIAS_RANGO = 90
DIAS_EXAMEN = 30
LOTE_DB = 200
MAX_CUERPO = 20000
MAX_XLSX_BYTES = 10 * 1024 * 1024
MAX_ENCABEZADOS = 40
MAX_FILAS_CONTADAS = 50000
VENTANA_REPLY = dt.timedelta(minutes=10)
HOLGURA_ANTES = dt.timedelta(seconds=5)
CAMBIO_MINIMO = dt.timedelta(seconds=2)
VENTANA_INIT = dt.timedelta(minutes=15)
PASO_SESGO = dt.timedelta(minutes=15)
SESGO_MAXIMO = dt.timedelta(hours=14)

HISTORICO = "historico"
SIN_EVIDENCIA = "sin_evidencia"
CIERRE = "cierre"

_PROHIBIDAS_SQL = re.compile(
    r"\b(INSERT|UPDATE|DELETE|MERGE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|COPY|CALL|DO|INTO|"
    r"VACUUM|LOCK|SET|COMMIT|BEGIN|ROLLBACK|REINDEX|CLUSTER|REFRESH|NOTIFY|EXECUTE|PREPARE|"
    r"SET_CONFIG|NEXTVAL|SETVAL|PG_ADVISORY\w*|PG_TERMINATE_BACKEND|PG_CANCEL_BACKEND|DBLINK\w*|LO_\w+)\b",
    re.IGNORECASE,
)
_SET_SOLO_LECTURA = "SET TRANSACTION READ ONLY"


class ConsultaNoPermitida(Exception):
    """Una consulta no es un SELECT puro: el script aborta."""


class LecturaNoPermitida(Exception):
    """Algo intentó pedir a Graph algo distinto de una consulta GET de lectura."""


# ------------------------------------------------------------------ solo lectura: PostgreSQL
def validar_select(sql: str) -> str:
    """Devuelve el SQL si es un único SELECT sin escritura; si no, aborta.

    Quita comentarios y literales antes de revisar. Rechaza ``;`` intermedios,
    CTE que escriben, ``SELECT INTO`` y ``FOR UPDATE``."""
    limpio = re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)
    limpio = re.sub(r"--[^\n]*", " ", limpio)
    limpio = re.sub(r"'(?:[^']|'')*'", "''", limpio)
    limpio = limpio.strip().rstrip(";").strip()
    if not re.match(r"SELECT\b", limpio, re.IGNORECASE):
        raise ConsultaNoPermitida("la consulta no empieza con SELECT")
    if ";" in limpio:
        raise ConsultaNoPermitida("más de una sentencia")
    prohibida = _PROHIBIDAS_SQL.search(limpio)
    if prohibida:
        raise ConsultaNoPermitida(f"palabra no permitida: {prohibida.group(1).upper()}")
    return sql


def cargar_sql(nombre: str, tablas: dict, querys_dir: str | None = None) -> str:
    with open(os.path.join(querys_dir or QUERYS_DIR, f"{nombre}.sql"), encoding="utf-8") as fh:
        sql = fh.read().format(**tablas)
    return validar_select(sql)


class LectorPG:
    """Conexión de solo lectura: ``SET TRANSACTION READ ONLY`` como primera
    sentencia, solo SELECT validados, rollback al cerrar (nunca commit)."""

    def __init__(self, conexion, tablas: dict, querys_dir: str | None = None):
        self._conn = conexion
        self._tablas = tablas
        self._querys_dir = querys_dir
        self._cur = conexion.cursor()
        self._cur.execute(_SET_SOLO_LECTURA)

    def consultar(self, nombre: str, *params) -> list[dict]:
        sql = cargar_sql(nombre, self._tablas, self._querys_dir)
        self._cur.execute(sql, params)
        return [dict(r) for r in self._cur.fetchall()]

    def cerrar(self) -> None:
        try:
            self._conn.rollback()
        finally:
            self._conn.close()


def abrir_pg_real():
    from infrastructure.database.postgres import get_connection

    return get_connection()


# ------------------------------------------------------------------ solo lectura: Graph
class LectorGraph:
    """Lector mínimo de Graph. Su única primitiva de red es un GET."""

    def __init__(self, obtener_token, http_get=None, dormir=time.sleep):
        if http_get is None:
            import requests

            http_get = requests.get
        self._token = obtener_token
        self._http_get = http_get
        self._dormir = dormir

    def get(self, ruta_o_url: str, params: dict | None = None, texto: bool = False) -> dict:
        url = ruta_o_url if ruta_o_url.startswith("http") else GRAPH_URL + ruta_o_url
        if not url.startswith(GRAPH_URL + "/"):
            raise LecturaNoPermitida("URL fuera de Microsoft Graph v1.0")
        token = self._token()
        if not token:
            raise RuntimeError("sin token de Graph")
        headers = {"Authorization": f"Bearer {token}"}
        if texto:
            headers["Prefer"] = 'outlook.body-content-type="text"'
        for intento in range(4):
            resp = self._http_get(url, headers=headers, params=params, timeout=60)
            if resp.status_code == 429 and intento < 3:
                self._dormir(float(resp.headers.get("Retry-After", 2 ** (intento + 1))))
                continue
            resp.raise_for_status()
            return resp.json()
        raise RuntimeError("Graph limitó la consulta (429)")

    def mensajes(self, buzon: str, desde: dt.datetime, hasta: dt.datetime, maximo: int) -> list[dict]:
        if maximo <= 0:
            return []
        params = {
            "$filter": (
                f"receivedDateTime ge {_iso(desde)} and receivedDateTime lt {_iso(hasta)} "
                "and isDraft eq false"
            ),
            "$orderby": "receivedDateTime desc",
            "$top": str(min(maximo, 50)),
            "$select": (
                "id,internetMessageId,conversationId,subject,from,toRecipients,"
                "receivedDateTime,hasAttachments,uniqueBody,body"
            ),
        }
        salida, url = [], f"/users/{buzon}/messages"
        while url and len(salida) < maximo:
            pag = self.get(url, params=params, texto=True)
            salida.extend(pag.get("value", []))
            url, params = pag.get("@odata.nextLink"), None
        return salida[:maximo]

    def adjuntos(self, buzon: str, mensaje_id: str) -> list[dict]:
        ruta = f"/users/{buzon}/messages/{mensaje_id}/attachments"
        lista = self.get(ruta, params={"$select": "id,name,contentType,size"}).get("value", [])
        for adj in lista:
            if _es_excel(adj) and (adj.get("size") or 0) <= MAX_XLSX_BYTES:
                completo = self.get(f"{ruta}/{adj['id']}")
                adj["contentBytes"] = completo.get("contentBytes")
        return lista


def _iso(d: dt.datetime) -> str:
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    return d.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _es_excel(adj: dict) -> bool:
    nombre = (adj.get("name") or "").lower()
    return nombre.endswith((".xlsx", ".xlsm")) or "spreadsheetml" in (adj.get("contentType") or "")


# ------------------------------------------------------------------ utilidades
def hash_id(valor) -> str | None:
    if not valor:
        return None
    return hashlib.sha256(str(valor).encode("utf-8")).hexdigest()[:16]


def _naive_utc(valor):
    if valor is None:
        return None
    if isinstance(valor, str):
        valor = dt.datetime.fromisoformat(valor.replace("Z", "+00:00"))
    if valor.tzinfo is not None:
        valor = valor.astimezone(dt.timezone.utc).replace(tzinfo=None)
    return valor


def _fecha_graph(texto: str) -> dt.datetime:
    return _naive_utc(texto)


def _redactar(texto, conservar=()):
    if not texto:
        return texto
    return redact(texto, conservar=conservar)


def cargar_buzones(ruta: str = EMAIL_INDEX) -> dict[str, str]:
    with open(ruta, encoding="utf-8") as fh:
        return {k.lower(): v for k, v in json.load(fh).items()}


def detectar_direccion(msg: dict, buzones: dict) -> tuple[str | None, str | None]:
    """(cliente, dirección) con la misma regla de ``EMAIL_TYPE.detect_direccion``."""
    remitente = msg["remitente"]
    destinatarios = msg["destinatarios"]
    rem_repare = remitente in buzones
    dest_repare = [d for d in destinatarios if d in buzones]
    if rem_repare and dest_repare:
        if "estimado usuario repare" in re.sub(r"\s+", " ", (msg["texto"] or "").lower()):
            return buzones[remitente], "bot"
        return buzones[remitente], "reply_to_bot"
    if dest_repare:
        return buzones[dest_repare[0]], "inbound"
    if rem_repare:
        return buzones[remitente], "outbound"
    return None, None


def normalizar_mensaje(crudo: dict, buzon: str) -> dict:
    de = ((crudo.get("from") or {}).get("emailAddress") or {}).get("address") or ""
    para = [
        ((r.get("emailAddress") or {}).get("address") or "").lower()
        for r in crudo.get("toRecipients") or []
    ]
    cuerpo = (crudo.get("uniqueBody") or {}).get("content") or (crudo.get("body") or {}).get("content") or ""
    return {
        "id": crudo["id"],
        "internet_id": crudo.get("internetMessageId"),
        "conversacion": crudo.get("conversationId"),
        "asunto": crudo.get("subject") or "",
        "texto": cuerpo[:MAX_CUERPO],
        "remitente": de.lower(),
        "destinatarios": [p for p in para if p],
        "recibido": _fecha_graph(crudo["receivedDateTime"]),
        "con_adjuntos": bool(crudo.get("hasAttachments")),
        "buzon": buzon,
    }


# ------------------------------------------------------------------ rangos y split
def calcular_rangos(desde: dt.datetime, hasta: dt.datetime, corte: dt.datetime, maximo: int):
    """[(inicio, fin, cupo, split)]. Con corte dentro del rango se reparte el
    cupo entre ajuste (la mitad) y examen (el resto) para que ambos existan."""
    if not desde < hasta:
        raise ValueError("--desde debe ser anterior a --hasta")
    if corte <= desde:
        return [(desde, hasta, maximo, "examen")]
    if corte >= hasta:
        return [(desde, hasta, maximo, "ajuste")]
    mitad = maximo // 2
    return [(desde, corte, mitad, "ajuste"), (corte, hasta, maximo - mitad, "examen")]


def asignar_split(recibido: dt.datetime, corte: dt.datetime) -> str:
    return "examen" if recibido >= corte else "ajuste"


# ------------------------------------------------------------------ adjuntos
def resumir_excel(contenido: bytes) -> dict:
    import openpyxl

    libro = openpyxl.load_workbook(io.BytesIO(contenido), read_only=True, data_only=True)
    hojas = []
    try:
        for hoja in libro.worksheets:
            encabezados, filas = None, 0
            for fila in hoja.iter_rows(values_only=True):
                if not any(c not in (None, "") for c in fila):
                    continue
                if encabezados is None:
                    encabezados = [
                        (_redactar(str(c).strip())[:60] if c not in (None, "") else "")
                        for c in fila[:MAX_ENCABEZADOS]
                    ]
                else:
                    filas += 1
                if filas >= MAX_FILAS_CONTADAS:
                    break
            hojas.append({"nombre": _redactar(str(hoja.title))[:60], "filas": filas, "encabezados": encabezados or []})
    finally:
        libro.close()
    return {"hojas": len(hojas), "filas": sum(h["filas"] for h in hojas), "detalle_hojas": hojas}


def resumir_adjuntos(adjuntos: list[dict]) -> list[dict]:
    """Solo nombre, tipo, hojas, filas y encabezados. Nunca el contenido."""
    salida = []
    for adj in adjuntos:
        info = {
            "nombre": _redactar(adj.get("name") or ""),
            "tipo": adj.get("contentType"),
        }
        b64 = adj.get("contentBytes")
        if b64:
            try:
                info.update(resumir_excel(base64.b64decode(b64)))
            except Exception as e:  # archivo roto o protegido: se anota y se sigue
                info["ilegible"] = type(e).__name__
        salida.append(info)
    return salida


# ------------------------------------------------------------------ etiquetado
class EstadoDB:
    """Resultados de las consultas, indexados para etiquetar sin más SQL."""

    def __init__(self, logs_msg, logs_conv, solicitudes, coolers):
        self.por_mensaje = {}
        for r in logs_msg:
            for clave in (r.get("graph_message_id"), r.get("internet_message_id")):
                if clave:
                    self.por_mensaje[clave] = r
        self.por_conv = collections.defaultdict(list)
        for r in logs_conv:
            self.por_conv[r.get("conversation_id")].append(r)
        for lista in self.por_conv.values():
            lista.sort(key=lambda r: (_naive_utc(r["created_at"]) or dt.datetime.min, r.get("id") or 0))
        self.solicitudes = {r["request_code"]: r for r in solicitudes}
        self.coolers = collections.defaultdict(list)
        for r in coolers:
            self.coolers[r["request_code"]].append(r)

    def log_de(self, msg: dict):
        return self.por_mensaje.get(msg["id"]) or self.por_mensaje.get(msg["internet_id"])

    def codigo_de_hilo(self, conversacion):
        for r in self.por_conv.get(conversacion, []):
            if r.get("request_code"):
                return r["request_code"]
        return None


def _filas_iniciales(filas: list[dict]) -> list[dict]:
    """Filas que nacieron con la solicitud: dentro de VENTANA_INIT de la primera."""
    if not filas:
        return []
    creadas = [_naive_utc(f["created_at"]) for f in filas if f.get("created_at")]
    if not creadas:
        return list(filas)
    primera = min(creadas)
    return [f for f in filas if not f.get("created_at") or _naive_utc(f["created_at"]) <= primera + VENTANA_INIT]


def calcular_sesgo(filas: list[dict], log_inicial: dict | None):
    """Diferencia de reloj entre cooler_request y emails_log, redondeada a 15 min.
    None si no se puede calibrar con seguridad."""
    if not log_inicial or not log_inicial.get("created_at"):
        return None
    creadas = [_naive_utc(f["created_at"]) for f in filas if f.get("created_at")]
    if not creadas:
        return None
    delta = min(creadas) - _naive_utc(log_inicial["created_at"])
    pasos = round(delta / PASO_SESGO)
    sesgo = pasos * PASO_SESGO
    if abs(sesgo) > SESGO_MAXIMO or abs(delta - sesgo) > VENTANA_INIT:
        return None
    return sesgo


def _estados(filas: list[dict]) -> dict:
    return dict(sorted(collections.Counter((f.get("status") or "?") for f in filas).items()))


def inferir_evento_reply(log_msg, logs_hilo, filas, sesgo, inicial_ids):
    """Qué hizo el mensaje de hilo sobre las filas, según los tiempos de la base.

    Devuelve (tipo_evento | None, es_os: bool | None, filas_esperadas, motivo)."""
    if sesgo is None:
        return None, None, [], "sin_calibracion_de_reloj"
    t0 = _naive_utc(log_msg["created_at"])
    if t0 is None:
        return None, None, [], "log_sin_fecha"
    lo, hi = t0 - HOLGURA_ANTES, t0 + VENTANA_REPLY
    for otro in logs_hilo:
        t = _naive_utc(otro.get("created_at"))
        if (
            t and t > t0 and otro.get("graph_message_id") != log_msg.get("graph_message_id")
            and (otro.get("direction") or "").lower() in ("inbound", "reply_to_bot")
        ):
            hi = min(hi, t)
    agregadas, tocadas = [], []
    for f in filas:
        creada = _naive_utc(f.get("created_at"))
        creada = creada - sesgo if creada else None
        actual = _naive_utc(f.get("updated_at"))
        actual = actual - sesgo if actual else None
        if creada and f["row_number"] not in inicial_ids and lo <= creada < hi:
            agregadas.append(f)
        elif actual and creada and lo <= actual < hi and actual - creada > CAMBIO_MINIMO:
            tocadas.append(f)
    canceladas = [f for f in tocadas if f.get("status") == "CANCELLED"]
    modificadas = [f for f in tocadas if f.get("status") != "CANCELLED"]
    tipos = []
    if agregadas:
        tipos.append("agregar_filas")
    if modificadas:
        tipos.append("modificar_filas")
    if canceladas:
        tipos.append("cancelar_filas")
    if not tipos:
        return None, None, [], "sin_cambios_en_la_ventana"
    esperadas = (
        [_fila_agregar(f) for f in agregadas]
        + [{"accion": "modificar", "row_number": f["row_number"]} for f in modificadas]
        + [{"accion": "cancelar", "row_number": f["row_number"]} for f in canceladas]
    )
    if len(tipos) > 1:
        return None, True, esperadas, "eventos_mezclados"
    return tipos[0], True, esperadas, "cambios_en_la_ventana"


def _fila_agregar(fila: dict) -> dict:
    out = {"accion": "agregar", "row_number": None}
    if fila.get("serie_fabricante"):
        out["serie_fabricante"] = fila["serie_fabricante"]
    if fila.get("serie_dnn_bnf"):
        out["serie_dnn_bnf"] = fila["serie_dnn_bnf"]
    return out


def etiquetar(msg: dict, estado: EstadoDB, buzones: dict) -> dict:
    """Etiqueta de un mensaje. Función pura sobre datos ya leídos.

    ``etapa``: init|reply · ``es_os``: True|None (jamás False) ·
    ``tipo_evento``: str|None · ``filas``: filas esperadas · ``evidencia``."""
    log = estado.log_de(msg)
    cliente_det, dir_det = detectar_direccion(msg, buzones)
    direccion = ((log or {}).get("direction") or dir_det or "").lower() or None
    cliente = (log or {}).get("customer") or cliente_det
    conv = (log or {}).get("conversation_id") or msg["conversacion"]
    logs_hilo = estado.por_conv.get(conv, [])
    codigo = (log or {}).get("request_code")
    etapa = _etapa(msg, log, logs_hilo)
    base = {
        "etapa": etapa, "cliente": cliente, "direccion": direccion, "es_os": None,
        "tipo_evento": None, "filas": [], "categoria": None, "thread_filas": None,
        "etiqueta_fuente": SIN_EVIDENCIA, "request_code": codigo,
        "evidencia": {"en_emails_log": log is not None},
    }
    if log is None:
        base["evidencia"]["motivo"] = "hilo_con_rastro_mensaje_sin_log" if logs_hilo else "sin_rastro_en_la_base"
        return base
    base["evidencia"]["procesamiento"] = log.get("processing_status")

    # Cierre: correo de REPARE con OS adjuntas al cliente.
    if direccion == "outbound":
        codigo = codigo or estado.codigo_de_hilo(conv)
        base["request_code"] = codigo
        filas = estado.coolers.get(codigo, []) if codigo else []
        con_os = [f for f in filas if f.get("os") not in (None, "")]
        if msg["con_adjuntos"] and con_os:
            base.update(es_os=True, categoria=CIERRE, etiqueta_fuente=HISTORICO)
            base["evidencia"].update(filas_con_os=len(con_os), filas_generadas=len(filas), estados=_estados(filas))
        else:
            base["evidencia"]["motivo"] = "saliente_sin_os_adjuntas"
        return base

    if not codigo:
        base["evidencia"]["motivo"] = "log_sin_solicitud"
        return base
    filas = estado.coolers.get(codigo, [])
    if not filas:
        base["evidencia"]["motivo"] = "solicitud_sin_filas" if codigo in estado.solicitudes else "solicitud_inexistente"
        return base

    iniciales = _filas_iniciales(filas)
    inicial_ids = {f["row_number"] for f in iniciales}
    log_inicial = next((r for r in logs_hilo if r.get("request_code") == codigo), None)
    sesgo = calcular_sesgo(filas, log_inicial)
    # Es el correo inicial si es el primer log de la solicitud y las filas nacieron junto a él.
    es_init = (
        log_inicial is not None
        and log_inicial.get("graph_message_id") == log.get("graph_message_id")
        and sesgo is not None
    )
    if es_init:
        base.update(
            etapa="init", es_os=True, tipo_evento="nueva_solicitud", etiqueta_fuente=HISTORICO,
        )
        base["evidencia"].update(
            filas_generadas=len(iniciales), estados=_estados(iniciales),
            filas_con_os=sum(1 for f in iniciales if f.get("os") not in (None, "")),
        )
        return base

    # Mensaje de hilo: contexto reconstruido y evento inferido por tiempos.
    tipo, es_os, esperadas, motivo = inferir_evento_reply(log, logs_hilo, filas, sesgo, inicial_ids)
    base["etapa"] = "reply"
    base["evidencia"]["motivo"] = motivo
    if es_os:
        base["es_os"] = True
        base["filas"] = esperadas
        base["evidencia"]["filas_afectadas"] = len(esperadas)
    if tipo:
        base["tipo_evento"] = tipo
        base["etiqueta_fuente"] = HISTORICO
    base["thread_filas"] = _contexto_hilo(filas, log, sesgo, inicial_ids, esperadas)
    return base


def _etapa(msg, log, logs_hilo) -> str:
    if log is not None:
        primero = next((r for r in logs_hilo if r.get("request_code") == log.get("request_code")), None)
        if primero is not None and primero.get("graph_message_id") != log.get("graph_message_id"):
            return "reply"
        return "init"
    if logs_hilo or re.match(r"\s*(re|rv|fw|fwd)\s*:", msg["asunto"], re.IGNORECASE):
        return "reply"
    return "init"


def _contexto_hilo(filas, log, sesgo, inicial_ids, esperadas) -> list[dict]:
    """Filas del hilo ANTES del mensaje, reconstruidas desde el estado actual:
    sin las filas que agregó el mensaje y con sus cancelaciones como PENDING.
    Es aproximado (lo que cambió después no se puede deshacer)."""
    t0 = _naive_utc(log["created_at"]) if log.get("created_at") else None
    canceladas = {e["row_number"] for e in esperadas if e["accion"] == "cancelar"}
    ctx = []
    for f in filas:
        creada = _naive_utc(f.get("created_at"))
        if sesgo is not None and t0 and creada and f["row_number"] not in inicial_ids and creada - sesgo >= t0 - HOLGURA_ANTES:
            continue
        status = "PENDING" if f["row_number"] in canceladas else f.get("status")
        ctx.append({
            "row_number": f["row_number"],
            "serie_fabricante": f.get("serie_fabricante"),
            "serie_dnn_bnf": f.get("serie_dnn_bnf"),
            "status": status if status in ("PENDING", "ACCEPTED", "CANCELLED", "REJECTED") else "PENDING",
        })
    return ctx


# ------------------------------------------------------------------ casos
def construir_caso(msg: dict, etiqueta: dict, adjuntos: list[dict], corte: dt.datetime) -> dict:
    """Único lugar donde se arma lo que se escribe: asunto y cuerpo SIEMPRE redactados."""
    series = [
        s for f in (etiqueta["thread_filas"] or []) for s in (f["serie_fabricante"], f["serie_dnn_bnf"]) if s
    ]
    caso = {
        "id": "bf-" + hash_id(msg["id"]),
        "fuente": "real",
        "etapa": etiqueta["etapa"],
        "cliente": etiqueta["cliente"],
        "direccion": etiqueta["direccion"],
        "asunto": _redactar(msg["asunto"], series),
        "cuerpo": _redactar(msg["texto"], series) or "",
        "esperado": {
            "es_os": etiqueta["es_os"],
            "tipo_evento": etiqueta["tipo_evento"],
            "filas": etiqueta["filas"] if etiqueta["etapa"] == "reply" else [],
        },
        "split": asignar_split(msg["recibido"], corte),
        "etiqueta_fuente": etiqueta["etiqueta_fuente"],
        "evidencia": etiqueta["evidencia"],
        "adjuntos": resumir_adjuntos(adjuntos),
        "ids": {
            "mensaje": hash_id(msg["id"]),
            "hilo": hash_id(msg["conversacion"]),
            "solicitud": hash_id(etiqueta["request_code"]),
        },
        "fecha": msg["recibido"].date().isoformat(),
    }
    if etiqueta["thread_filas"] is not None:
        caso["thread_ctx"] = {"filas": etiqueta["thread_filas"]}
        caso["ctx_aproximado"] = True
    if etiqueta["categoria"]:
        caso["categoria"] = etiqueta["categoria"]
    if re.search(r"@\S+\.\S+", caso["asunto"] + " " + caso["cuerpo"]):
        caso["revisar_pii"] = True
    return caso


def escribir_jsonl(ruta: str, casos: list[dict]) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(ruta)), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as fh:
        for c in casos:
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")


def ruta_revision(salida: str) -> str:
    raiz, ext = os.path.splitext(salida)
    return f"{raiz}_revision{ext or '.jsonl'}"


# ------------------------------------------------------------------ ejecución
def _lotes(valores: list, n: int = LOTE_DB):
    valores = list(valores)
    for i in range(0, len(valores), n):
        yield valores[i:i + n]


def leer_estado(pg: LectorPG, mensajes: list[dict]) -> EstadoDB:
    ids = sorted({m["id"] for m in mensajes})
    internet = sorted({m["internet_id"] for m in mensajes if m["internet_id"]})
    logs_msg = []
    for lote in _lotes(ids):
        logs_msg += pg.consultar("logs_por_mensaje", lote, [])
    for lote in _lotes(internet):
        logs_msg += pg.consultar("logs_por_mensaje", [], lote)
    convs = sorted({m["conversacion"] for m in mensajes if m["conversacion"]} | {r["conversation_id"] for r in logs_msg if r.get("conversation_id")})
    logs_conv = []
    for lote in _lotes(convs):
        logs_conv += pg.consultar("logs_por_conversacion", lote)
    codigos = sorted({r["request_code"] for r in logs_msg + logs_conv if r.get("request_code")})
    solicitudes, coolers = [], []
    for lote in _lotes(codigos):
        solicitudes += pg.consultar("solicitudes", lote)
        coolers += pg.consultar("coolers", lote)
    return EstadoDB(logs_msg, logs_conv, solicitudes, coolers)


def correr(args, graph: LectorGraph, pg: LectorPG, hoy: dt.date) -> dict:
    buzones = cargar_buzones(args.config)
    lista = [b.lower() for b in (args.buzones or buzones)]
    corte, desde, hasta = args.corte_dt, args.desde_dt, args.hasta_dt

    mensajes, omitidos_bot = [], 0
    for buzon in lista:
        for inicio, fin, cupo, _split in calcular_rangos(desde, hasta, corte, args.maximo):
            for crudo in graph.mensajes(buzon, inicio, fin, cupo):
                mensajes.append(normalizar_mensaje(crudo, buzon))
    estado = leer_estado(pg, mensajes)

    casos, vistos = [], set()
    for msg in mensajes:
        if msg["id"] in vistos:
            continue
        vistos.add(msg["id"])
        etiqueta = etiquetar(msg, estado, buzones)
        if etiqueta["direccion"] == "bot":
            omitidos_bot += 1
            continue
        adjuntos = graph.adjuntos(msg["buzon"], msg["id"]) if msg["con_adjuntos"] else []
        casos.append(construir_caso(msg, etiqueta, adjuntos, corte))

    revision = [c for c in casos if c["etiqueta_fuente"] == SIN_EVIDENCIA or c["esperado"]["tipo_evento"] is None]
    escribir_jsonl(args.salida, casos)
    escribir_jsonl(ruta_revision(args.salida), revision)
    return resumen(casos, revision, omitidos_bot, args)


def resumen(casos, revision, omitidos_bot, args) -> dict:
    return {
        "casos": len(casos),
        "historico": sum(c["etiqueta_fuente"] == HISTORICO for c in casos),
        "sin_evidencia": sum(c["etiqueta_fuente"] == SIN_EVIDENCIA for c in casos),
        "revision": len(revision),
        "por_split": dict(collections.Counter(c["split"] for c in casos)),
        "por_tipo": dict(collections.Counter(str(c["esperado"]["tipo_evento"]) for c in casos)),
        "con_cierre": sum(c.get("categoria") == CIERRE for c in casos),
        "omitidos_bot": omitidos_bot,
        "salida": args.salida,
        "salida_revision": ruta_revision(args.salida),
    }


# ------------------------------------------------------------------ main
def _fecha(texto: str) -> dt.datetime:
    return dt.datetime.strptime(texto, "%Y-%m-%d")


def parsear(argv, hoy: dt.date):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--buzones", nargs="+", help="buzones a leer (default: los de config/email_index.json)")
    ap.add_argument("--desde", help=f"YYYY-MM-DD, incluido (default: {DIAS_RANGO} días antes de --hasta)")
    ap.add_argument("--hasta", help="YYYY-MM-DD, excluido (default: mañana)")
    ap.add_argument("--maximo", type=int, default=MAX_POR_BUZON, help="máximo de correos por buzón (default 100)")
    ap.add_argument("--tablas", choices=("qa", "prod"), default="qa")
    ap.add_argument("--confirmo-solo-lectura", action="store_true", help="obligatorio con --tablas prod")
    ap.add_argument("--corte", help=f"YYYY-MM-DD: desde esta fecha el split es examen (default: últimos {DIAS_EXAMEN} días)")
    ap.add_argument("--salida", help="JSONL de salida (default eval/sets/real/backfill_<fecha>.jsonl)")
    ap.add_argument("--config", default=EMAIL_INDEX, help=argparse.SUPPRESS)
    ap.add_argument("--hash", dest="hash_id", help="imprime el hash de un id de mensaje y sale")
    args = ap.parse_args(argv)
    if args.hash_id:
        return args
    if args.maximo < 1:
        ap.error("--maximo debe ser >= 1")
    if args.tablas == "prod" and not args.confirmo_solo_lectura:
        ap.error("--tablas prod exige --confirmo-solo-lectura (usa un usuario de base de solo lectura si existe)")
    try:
        manana = dt.datetime.combine(hoy, dt.time()) + dt.timedelta(days=1)
        args.hasta_dt = _fecha(args.hasta) if args.hasta else manana
        args.desde_dt = _fecha(args.desde) if args.desde else args.hasta_dt - dt.timedelta(days=DIAS_RANGO)
        args.corte_dt = _fecha(args.corte) if args.corte else dt.datetime.combine(hoy, dt.time()) - dt.timedelta(days=DIAS_EXAMEN)
    except ValueError as e:
        ap.error(f"fecha inválida: {e}")
    if not args.desde_dt < args.hasta_dt:
        ap.error("--desde debe ser anterior a --hasta")
    if args.salida is None:
        args.salida = os.path.join(SALIDA_DIR, f"backfill_{hoy.isoformat()}.jsonl")
    return args


def main(argv=None, *, graph: LectorGraph | None = None, abrir_pg=None, hoy: dt.date | None = None) -> int:
    hoy = hoy or dt.date.today()
    try:
        args = parsear(argv, hoy)
    except SystemExit as e:
        return int(e.code or 0)
    if args.hash_id:
        print(hash_id(args.hash_id))
        return 0
    if graph is None:
        from infrastructure.graphapi.graphapi import getToken

        graph = LectorGraph(getToken)
    pg = None
    try:
        pg = LectorPG((abrir_pg or abrir_pg_real)(), TABLAS[args.tablas])
        res = correr(args, graph, pg, hoy)
    except (ConsultaNoPermitida, LecturaNoPermitida) as e:
        print(f"ABORTADO (solo lectura): {e}", file=sys.stderr)
        return 3
    except Exception as e:
        print(f"Falló el backfill: {type(e).__name__}", file=sys.stderr)
        return 4
    finally:
        if pg is not None:
            pg.cerrar()
    print(f"== Backfill e2c (solo lectura) · tablas={args.tablas} · casos={res['casos']} ==")
    print(f"histórico {res['historico']} · sin evidencia {res['sin_evidencia']} · cierres {res['con_cierre']} · bot omitidos {res['omitidos_bot']}")
    print(f"split {res['por_split']} · tipos {res['por_tipo']}")
    print(f"salida: {res['salida']}\nrevisión humana ({res['revision']}): {res['salida_revision']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

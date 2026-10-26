"""Qué pide un correo de Imbera/Torrey, leído del CONTENIDO (no de la
cuenta): tipo de solicitud, variante de ruta, sub-cliente, folio
IMB-/REP- y señales de garantía. Solo regex y reglas fijas; no llama a
ningún proveedor externo (el Excel puede traer PII)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from config.customers.imbera import reglas_imbera as R
from parsers.imbera_parse.lector import normalizar

_PREFIJOS = re.compile(r"^\s*((RE|RV|FW|FWD)\s*:\s*)+", re.IGNORECASE)


def limpiar_asunto(asunto: str | None) -> str:
    """Sin RE:/RV:/FW:, normalizado y con los guiones '--' uniformes."""
    texto = normalizar(_PREFIJOS.sub("", asunto or ""))
    return re.sub(r"\s*-{2,}\s*", " -- ", texto).strip()


@dataclass
class Clasificacion:
    # ruta | movimiento | garantia | seguimiento | desconocido
    tipo: str = "desconocido"
    # folio_app | proyecto_especial | distribuidora (solo ruta)
    variante_ruta: str | None = None
    subcliente: str | None = None
    plaza: str | None = None
    movimiento: str | None = None
    folio: str | None = None  # IMB-ddmmaa_n / REP-ddmmaa_n
    folio_app: str | None = None
    os_asunto: str | None = None
    senales_garantia: list[str] = field(default_factory=list)

    @property
    def garantia(self) -> bool:
        return bool(self.senales_garantia)


def _subcliente_conocido(texto: str) -> tuple[str, str] | None:
    """(sub-cliente, resto del texto) si `texto` menciona uno conocido."""
    for palabra, nombre in R.SUBCLIENTES.items():
        m = re.search(rf"\b{re.escape(palabra)}\b", texto)
        if m:
            resto = (texto[:m.start()] + " " + texto[m.end():]).strip(" -")
            return nombre, " ".join(resto.split()) or None
    return None


def _desde_asunto(c: Clasificacion, asunto: str) -> None:
    for tipo, patron in R.ASUNTOS:
        m = patron.search(asunto)
        if not m:
            continue
        c.tipo = tipo
        grupos = m.groupdict()
        c.movimiento = grupos.get("movimiento")
        crudo = (grupos.get("cliente") or "").strip()
        # Quita el folio u OS que a veces viene pegado al final.
        crudo = R.PATRON_FOLIO.sub("", crudo).strip(" -")
        if crudo:
            conocido = _subcliente_conocido(crudo)
            if conocido:
                c.subcliente, plaza = conocido
                c.plaza = grupos.get("plaza") or plaza
            else:
                # TODO(sub-cliente): sin catálogo no se separa cliente de
                # plaza; se guarda el texto tal cual.
                c.subcliente = crudo
                c.plaza = grupos.get("plaza")
        elif grupos.get("plaza"):
            c.plaza = grupos["plaza"]
        return


def _senales_garantia(asunto, cuerpo, adjuntos, buzones) -> list[str]:
    senales = []
    if R.PATRON_GARANTIA.search(asunto):
        senales.append("asunto")
    pdfs = [a for a in adjuntos if Path(a).suffix.lower() == ".pdf"]
    # TODO(garantía): cualquier PDF cuenta como factura; sin leer el PDF no
    # se distingue una factura de otro documento.
    if pdfs:
        senales.append("factura_pdf")
    if any(
        Path(a).suffix.lower() in R.EXTENSIONES_IMAGEN and R.PATRON_FOTO_PLACA.search(a)
        for a in adjuntos
    ):
        senales.append("foto_placa")
    if R.PATRON_EQUIPO_NUEVO_DANADO.search(cuerpo):
        senales.append("equipo_nuevo_danado")
    if any(R.PATRON_BUZON_GARANTIAS.search(b or "") for b in buzones):
        senales.append("buzon_garantias")
    return senales


def clasificar(
    asunto: str | None,
    cuerpo: str | None,
    adjuntos: list[str] = (),
    buzones: list[str] = (),
) -> Clasificacion:
    """`adjuntos`: nombres de archivo; `buzones`: remitente, To y CC."""
    asunto_n = limpiar_asunto(asunto)
    cuerpo_n = normalizar(cuerpo)
    c = Clasificacion()

    folio = R.PATRON_FOLIO.search(asunto_n)
    c.folio = folio.group(1).upper() if folio else None
    os_asunto = R.PATRON_OS_ASUNTO.search(asunto_n)
    c.os_asunto = os_asunto.group(1) if os_asunto else None

    _desde_asunto(c, asunto_n)

    if c.subcliente is None:
        conocido = _subcliente_conocido(f"{asunto_n} {cuerpo_n}")
        if conocido:
            c.subcliente = conocido[0]

    folio_app = R.PATRON_FOLIO_APP.search(f"{asunto_n} {cuerpo_n}")
    c.folio_app = folio_app.group(1) if folio_app else None

    if c.tipo == "desconocido" and R.PATRON_SEGUIMIENTO.search(asunto_n):
        c.tipo = "seguimiento"

    c.senales_garantia = _senales_garantia(asunto_n, cuerpo_n, list(adjuntos), list(buzones))
    if c.tipo == "desconocido" and c.garantia:
        c.tipo = "garantia"

    if c.tipo in ("ruta", "garantia", "desconocido"):
        if c.folio_app:
            c.variante_ruta = "folio_app"
        elif R.PATRON_PROYECTO_ESPECIAL.search(f"{asunto_n} {cuerpo_n}"):
            c.variante_ruta = "proyecto_especial"
        else:
            c.variante_ruta = "distribuidora"

    return c

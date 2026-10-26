"""Respuesta de Imbera/Torrey: misma caja que msj_send_presabana, más la
tabla de filas aceptadas y rechazadas (solo fila, serie, modelo, cliente
de la OS, garantía y motivo: sin PII) y los avisos de la solicitud."""

from __future__ import annotations

from html import escape

_CELDA = "padding:4px 10px;border-top:1px solid #d0d7de;"


def _tabla(filas: list[dict], con_motivo: bool) -> str:
    encabezados = ["Fila", "Serie", "Modelo", "Cliente OS", "Garantía"] + (["Motivo"] if con_motivo else [])
    cabecera = "".join(f"<th style='padding:4px 10px;text-align:left;'>{h}</th>" for h in encabezados)
    cuerpo = ""
    for f in filas:
        valores = [
            f.get("fila"), f.get("serie"), f.get("modelo"), f.get("cliente"),
            "SI" if f.get("garantia") else "NO",
        ] + ([f.get("motivo")] if con_motivo else [])
        cuerpo += "<tr>" + "".join(
            f"<td style='{_CELDA}'>{escape(str(v or '-'))}</td>" for v in valores
        ) + "</tr>"
    return (
        '<table style="border-collapse:collapse;margin-top:10px;font-size:13px;">'
        f'<tr style="color:#57606a;">{cabecera}</tr>{cuerpo}</table>'
    )


def _seccion(titulo: str, contenido: str) -> str:
    return f"""
            <div style="
                margin-top: 18px;
                padding: 14px 16px;
                border: 1px solid #d0d7de;
                border-radius: 6px;
                background: #ffffff;
            ">
                <div style="font-size: 12px; color: #57606a; margin-bottom: 5px;">
                    {titulo}
                </div>
                {contenido}
            </div>
    """


def msj_solicitud_layout(
    folio: str,
    aceptadas: list[dict],
    rechazadas: list[dict],
    avisos: list[str] = (),
    actualizacion: bool = False,
) -> str:
    """Solicitud nueva (REQUEST RECEIVED) o filas agregadas por el cliente
    en el hilo (REQUEST UPDATED)."""
    titulo = "REQUEST UPDATED" if actualizacion else "REQUEST RECEIVED"
    detalle = (
        "Recibimos la actualización de su solicitud."
        if actualizacion else
        "Hemos recibido su solicitud y ha iniciado\n                    el <b>proceso de validación</b>."
    )
    secciones = _seccion(
        "FOLIO",
        f'<div style="font-size: 18px; font-weight: bold; letter-spacing: 1px;">{escape(str(folio))}</div>',
    )
    secciones += _seccion(
        f"ACEPTADAS ({len(aceptadas)})",
        _tabla(aceptadas, con_motivo=False) if aceptadas else '<div style="color:#57606a;">Ninguna</div>',
    )
    secciones += _seccion(
        f"RECHAZADAS ({len(rechazadas)})",
        _tabla(rechazadas, con_motivo=True) if rechazadas else '<div style="color:#57606a;">Ninguna</div>',
    )
    if avisos:
        secciones += _seccion(
            "AVISOS",
            "<ul style='margin:0;padding-left:18px;color:#57606a;'>"
            + "".join(f"<li>{escape(a)}</li>" for a in avisos)
            + "</ul>",
        )

    return f"""
        <div style="
            font-family: ui-monospace, SFMono-Regular, SF Mono, Menlo, Monaco,
                        Consolas, 'Liberation Mono', 'Courier New', monospace;
            max-width: 680px;
            color: #24292f;
            font-size: 14px;
            line-height: 1.6;
        ">

            <p style="font-size: 15px; margin-bottom: 20px;">
                🤖 Estimado usuario REPARE,
            </p>

            <div style="
                border: 1px solid #d0d7de;
                border-radius: 6px;
                padding: 20px;
                background: #f6f8fa;
            ">
                <div style="font-size: 14px; font-weight: bold; margin-bottom: 12px;">
                    {titulo}
                </div>
                <div style="color: #57606a;">
                    {detalle}
                </div>
            </div>
            {secciones}
            <p style="color: #57606a; margin-top: 18px;">
                Se adjunta la <b>pre-sábana</b> correspondiente a su solicitud.
            </p>

        </div>
        """

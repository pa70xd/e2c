"""Respuestas de Oxxo a REPARE. Mismo estilo que MENSAJES_REPARE. Solo llevan
códigos (folio REPARE, ticket o folio de Oxxo, conteos): nada de PII."""

from html import escape

_CONTENEDOR = """
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
                    {texto}
                </div>

            </div>
            {extra}
        </div>
"""


def _caja(etiqueta: str, valor: str) -> str:
    return f"""
            <div style="
                margin-top: 18px;
                padding: 14px 16px;
                border: 1px solid #d0d7de;
                border-radius: 6px;
                background: #ffffff;
            ">
                <div style="font-size: 12px; color: #57606a; margin-bottom: 5px;">{escape(etiqueta)}</div>
                <div style="font-size: 18px; font-weight: bold; letter-spacing: 1px;">{escape(valor)}</div>
            </div>
    """


def _enlace(url: str | None) -> str:
    if not url:
        return ""
    return f"""
            <p style="color: #57606a; margin-top: 18px;">
                Correo original: <a href="{escape(str(url))}">abrir</a>
            </p>
    """


class MENSAJES_OXXO:

    def msj_os_registrada(self, request_code: str, etiqueta: str, folio: str, url=None, aviso=None):
        """OS nueva registrada. ``etiqueta`` es 'TICKET' o 'FOLIO'; ``aviso``
        (opcional) es un texto fijo, p. ej. que el folio escalado no existía."""
        texto = "Se registró una <b>OS nueva</b>."
        if aviso:
            texto += f"<br><b>Aviso:</b> {escape(aviso)}"
        extra = _caja("FOLIO REPARE", request_code) + _caja(etiqueta, folio) + _enlace(url)
        return _CONTENEDOR.format(titulo="REQUEST RECEIVED", texto=texto, extra=extra)

    def msj_excel_registrado(self, request_code: str, total: int, url=None):
        texto = f"Se registraron <b>{int(total)}</b> OS desde el Excel adjunto."
        extra = _caja("FOLIO REPARE", request_code) + _enlace(url)
        return _CONTENEDOR.format(titulo="REQUEST RECEIVED", texto=texto, extra=extra)

"""Mensajes de KOF: los de MENSAJES_REPARE más el conteo de aceptadas y
rechazadas (el detalle va en el Excel de resultado)."""

from config.config_general.messages import MENSAJES_REPARE

_CONTEO = """
        <div style="
            font-family: ui-monospace, SFMono-Regular, SF Mono, Menlo, Monaco,
                        Consolas, 'Liberation Mono', 'Courier New', monospace;
            max-width: 680px;
            color: #57606a;
            font-size: 13px;
            margin-top: 12px;
        ">
            ACEPTADAS&nbsp;=&nbsp;<code>{aceptadas}</code>&nbsp;&nbsp;
            RECHAZADAS&nbsp;=&nbsp;<code>{rechazadas}</code><br>
            El detalle por fila va en el archivo RESULTADO_KOF adjunto.
        </div>
        """


_SIN_ACEPTADAS = """
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
                    REQUEST REJECTED
                </div>
                <div style="color: #57606a;">
                    Ninguna fila del archivo cumple con los datos mínimos;
                    no se generó folio.
                </div>
            </div>
        </div>
        """


class MENSAJES_KOF(MENSAJES_REPARE):

    @staticmethod
    def conteo(aceptadas: int, rechazadas: int) -> str:
        return _CONTEO.format(aceptadas=aceptadas, rechazadas=rechazadas)

    def msj_init_kof(self, request_code, url, aceptadas, rechazadas):
        return self.msj_send_presabana(request_code, url) + self.conteo(aceptadas, rechazadas)

    def msj_add_kof(self, request_code, url, aceptadas, rechazadas):
        return self.msj_add_cliente(request_code, url) + self.conteo(aceptadas, rechazadas)

    def msj_sin_aceptadas(self, rechazadas):
        return _SIN_ACEPTADAS + self.conteo(0, rechazadas)

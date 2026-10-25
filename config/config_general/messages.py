#mensaje inicial de apertura
class MENSAJES_REPARE:

    def msj_send_presabana(self, folio: str, url: str):
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

                <div style="
                    font-size: 14px;
                    font-weight: bold;
                    margin-bottom: 12px;
                ">
                    REQUEST RECEIVED
                </div>

                <div style="color: #57606a;">
                    Hemos recibido su solicitud y ha iniciado
                    el <b>proceso de validación</b>.
                </div>

            </div>

            <div style="
                margin-top: 18px;
                padding: 14px 16px;
                border: 1px solid #d0d7de;
                border-radius: 6px;
                background: #ffffff;
            ">

                <div style="
                    font-size: 12px;
                    color: #57606a;
                    margin-bottom: 5px;
                ">
                    FOLIO
                </div>

                <div style="
                    font-size: 18px;
                    font-weight: bold;
                    letter-spacing: 1px;
                ">
                    {folio}
                </div>

            </div>

            <p style="
                color: #57606a;
                margin-top: 18px;
            ">
                Se adjunta la <b>pre-sábana</b> correspondiente a su solicitud.
            </p>

        </div>
        """



#----------------------------------------------------nuevo mensaje
    def formato_desconocido(self):
        return """
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

                <div style="
                    font-size: 14px;
                    font-weight: bold;
                    margin-bottom: 12px;
                ">
                    REQUEST FAILED
                </div>

                <div style="color: #57606a;">
                    El archivo recibido presenta un
                    <b>formato desconocido o no compatible</b>.
                </div>

            </div>

            <p style="
                color: #57606a;
                margin-top: 18px;
            ">
                Verifique el formato del archivo y envíe nuevamente
                la solicitud utilizando un archivo compatible.
            </p>

            <div style="
                margin-top: 20px;
                padding: 10px 12px;
                border-left: 3px solid #d0d7de;
                color: #57606a;
                font-size: 12px;
            ">
                STATUS&nbsp;&nbsp;=&nbsp;&nbsp;<code>ERROR</code><br>
                CODE&nbsp;&nbsp;&nbsp;=&nbsp;&nbsp;<code>archivo adjuntos</code>
            </div>

        </div>
        """
#==================================================================================





    def msj_add_cliente(self, folio: str, url: str):
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

                <div style="
                    font-size: 14px;
                    font-weight: bold;
                    margin-bottom: 12px;
                ">
                    REQUEST UPDATED
                </div>

                <div style="color: #57606a;">
                    Se ha detectado una nueva solicitud o actualización
                    y se ha generado la <b>pre-sábana</b> correspondiente.
                </div>

            </div>

            <div style="
                margin-top: 18px;
                padding: 14px 16px;
                border: 1px solid #d0d7de;
                border-radius: 6px;
                background: #ffffff;
            ">

                <div style="
                    font-size: 12px;
                    color: #57606a;
                    margin-bottom: 5px;
                ">
                    FOLIO
                </div>

                <div style="
                    font-size: 18px;
                    font-weight: bold;
                    letter-spacing: 1px;
                ">
                    {folio}
                </div>

            </div>

        </div>
        """






    def msj_fail(self):
        return """
        <html>
        <body style="font-family:Segoe UI,Arial,sans-serif;font-size:14px;color:#333;">
            <p><b>🤖 Estimado usuario REPARE,</b></p>

            <p>No fue posible preparar el archivo solicitado.</p>
        </body>
        </html>
        """


    











    def msj_ayuda(self):
        return """
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

                <div style="
                    font-size: 14px;
                    font-weight: bold;
                    margin-bottom: 16px;
                ">
                    AVAILABLE COMMANDS
                </div>

                <div style="color: #57606a;">

                    <b>[bot.help]</b><br>
                    Consulta los comandos disponibles.<br><br>

                    <b>[bot.estatus]</b><br>
                    Consulta el estatus actual de una solicitud.<br><br>

                    <b>[bot.cancelar]</b><br>
                    Solicita la cancelación de una solicitud.<br><br>

                    <b>[bot.finalizar]</b><br>
                    Solicita la finalización de una solicitud.<br><br>

                    <b>[bot.global]</b><br>
                    Solicita el documento con el estatus global de solicitudes.

                </div>

            </div>

            <p style="
                color: #57606a;
                margin-top: 18px;
            ">
                <b>Importante:</b> Responde únicamente al correo del bot
                para ejecutar los comandos.
            </p>

        </div>
        """


    def msj_cancelar(self, request_code):
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

                <div style="
                    font-size: 14px;
                    font-weight: bold;
                    margin-bottom: 12px;
                ">
                    REQUEST CANCELLED
                </div>

                <div style="color: #57606a;">
                    La solicitud <b>{request_code}</b> fue
                    <b>cancelada correctamente</b>.
                </div>

            </div>

            <p style="
                color: #57606a;
                margin-top: 18px;
            ">
                La solicitud ya no continuará con su procesamiento.
            </p>

            <p style="color: #57606a;">
                Si necesita generar una nueva solicitud, puede responder
                nuevamente al correo del bot.
            </p>

        </div>
        """



    def msj_finalizar(self, request_code):
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

                <div style="
                    font-size: 14px;
                    font-weight: bold;
                    margin-bottom: 12px;
                ">
                    REQUEST COMPLETED
                </div>

                <div style="color: #57606a;">
                    La solicitud <b>{request_code}</b> fue
                    <b>finalizada correctamente</b>.
                </div>

            </div>

        </div>
        """



 
    def msj_solicitud_completa_esc1(
        self,
        folio: str,
        url: str,
        total: int,
        con_os: int,
        sin_os: int,
    ):
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

                <div style="
                    font-size: 14px;
                    font-weight: bold;
                    margin-bottom: 12px;
                ">
                    REQUEST COMPLETED
                </div>

                <div style="color: #57606a;">
                    La solicitud <b>{folio}</b> ha sido
                    <b>finalizada correctamente</b>.
                </div>

            </div>

            <div style="
                margin-top: 18px;
                border: 1px solid #d0d7de;
                border-radius: 6px;
                padding: 14px 16px;
                background: #ffffff;
            ">

                <div style="
                    font-size: 12px;
                    color: #57606a;
                    margin-bottom: 8px;
                ">
                    RESUMEN
                </div>

                <div style="color: #57606a;">
                    <b>{total}</b> equipos procesados<br>
                    <b>{con_os}</b> equipos con OS asignada<br>
                    <b>{sin_os}</b> equipos sin OS asignada
                </div>

            </div>

        </div>
        """



    
    def msj_cambios(
        self,
        folio: str,
        url: str,
        total: int,
        con_os: int,
        sin_os: int,
        desconocidos: int,
    ):
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

                <div style="
                    font-size: 14px;
                    font-weight: bold;
                    margin-bottom: 12px;
                ">
                    CHANGES APPLIED
                </div>

                <div style="color: #57606a;">
                    Los cambios de la solicitud <b>{folio}</b>
                    han sido aplicados correctamente.
                </div>

            </div>

            <div style="
                margin-top: 18px;
                border: 1px solid #d0d7de;
                border-radius: 6px;
                padding: 14px 16px;
                background: #ffffff;
            ">

                <div style="
                    font-size: 12px;
                    color: #57606a;
                    margin-bottom: 8px;
                ">
                    RESUMEN
                </div>

                <div style="color: #57606a;">
                    <b>{total}</b> equipos procesados<br>
                    <b>{con_os}</b> equipos con OS (ACEPTADOS)<br>
                    <b>{sin_os}</b> equipos sin OS (PENDIENTES)<br>
                    <b>{desconocidos}</b> equipos sin OS (RECHAZADOS)
                </div>

            </div>

        </div>
        """

    def msj_status_solicitud(self, data):

        status_map = {
            "IN_PROGRESS": "En proceso",
            "COMPLETED": "Completada",
            "PENDING": "Pendiente",
            "CANCELLED": "Cancelada",
        }

        status = status_map.get(
            data["status"],
            data["status"]
        )

        mensaje = f"""
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

                <div style="
                    font-size: 14px;
                    font-weight: bold;
                    margin-bottom: 12px;
                ">
                    REQUEST STATUS
                </div>

                <div style="color: #57606a;">
                    <b>FOLIO</b>&nbsp;&nbsp; {data["request_code"]}<br>
                    <b>STATUS</b>&nbsp; {status}
                </div>

            </div>

            <div style="
                margin-top: 18px;
                border: 1px solid #d0d7de;
                border-radius: 6px;
                padding: 14px 16px;
                background: #ffffff;
            ">

                <div style="
                    font-size: 12px;
                    color: #57606a;
                    margin-bottom: 8px;
                ">
                    EQUIPMENT SUMMARY
                </div>

                <div style="color: #57606a;">
                    <b>{data["completed_coolers"]}</b> equipos completados<br>
                    <b>{data["pending_coolers"]}</b> equipos pendientes<br>
                    <b>{data["failed_coolers"]}</b> equipos cancelados<br>
                    <b>{data["total_coolers"]}</b> equipos totales
                </div>

            </div>
        """

        if data.get("tickets_accepted"):
            mensaje += """
            <div style="
                margin-top: 18px;
                padding: 14px 16px;
                border: 1px solid #d0d7de;
                border-radius: 6px;
                background: #ffffff;
            ">
                <div style="
                    font-size: 12px;
                    color: #57606a;
                    margin-bottom: 8px;
                ">
                    COMPLETED TICKETS
                </div>
            """
            for ticket in data["tickets_accepted"]:
                mensaje += f"<div>{ticket}</div>"

            mensaje += "</div>"

        if data.get("tickets_pending"):
            mensaje += """
            <div style="
                margin-top: 18px;
                padding: 14px 16px;
                border: 1px solid #d0d7de;
                border-radius: 6px;
                background: #ffffff;
            ">
                <div style="
                    font-size: 12px;
                    color: #57606a;
                    margin-bottom: 8px;
                ">
                    PENDING TICKETS
                </div>
            """
            for ticket in data["tickets_pending"]:
                mensaje += f"<div>{ticket}</div>"

            mensaje += "</div>"

        if data.get("tickets_cancelled"):
            mensaje += """
            <div style="
                margin-top: 18px;
                padding: 14px 16px;
                border: 1px solid #d0d7de;
                border-radius: 6px;
                background: #ffffff;
            ">
                <div style="
                    font-size: 12px;
                    color: #57606a;
                    margin-bottom: 8px;
                ">
                    CANCELLED TICKETS
                </div>
            """
            for ticket in data["tickets_cancelled"]:
                mensaje += f"<div>{ticket}</div>"

            mensaje += "</div>"

        mensaje += """
        </div>
        """

        return mensaje


    def msj_comando_no_reconocido(self):
        return """
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

                <div style="
                    font-size: 14px;
                    font-weight: bold;
                    margin-bottom: 12px;
                ">
                    COMMAND NOT RECOGNIZED
                </div>

                <div style="color: #57606a;">
                    No se reconoció la palabra o comando enviado.
                    Verifique la información e intente nuevamente.
                </div>

            </div>

            <p style="
                color: #57606a;
                margin-top: 18px;
            ">
                Para consultar los comandos disponibles, escriba
                <b>[bot.help]</b>.
            </p>

        </div>
        """


    def msj_folio_requerido(self, folio: str | None = None):
        """Genérico (no exclusivo de un cliente): se usa cuando un comando
        del bot no puede resolver sobre qué solicitud actuar -- p. ej. en
        hilos que agrupan varias solicitudes, como el de Holanda. Si
        `folio` viene, significa que se encontró pero no existe/no es de
        ese cliente; si no, que no se encontró ninguno."""

        if folio:
            detalle = (
                f"No se encontró la solicitud <b>{folio}</b>. "
                "Verifique el folio e intente nuevamente."
            )
        else:
            detalle = (
                "No se pudo identificar la solicitud a la que se refiere "
                "el comando."
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

                <div style="
                    font-size: 14px;
                    font-weight: bold;
                    margin-bottom: 12px;
                ">
                    FOLIO REQUIRED
                </div>

                <div style="color: #57606a;">
                    {detalle}
                </div>

            </div>

            <p style="
                color: #57606a;
                margin-top: 18px;
            ">
                Responda al correo del bot que contiene el folio, o
                escríbalo junto al comando, por ejemplo:
                <b>bot.estatus REPARE_000157</b>.
            </p>

        </div>
        """


    def msj_global(self):
        return """
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

                <div style="
                    font-size: 14px;
                    font-weight: bold;
                    margin-bottom: 12px;
                ">
                    GLOBAL STATUS
                </div>

                <div style="color: #57606a;">
                    Consulta global completada correctamente.
                </div>

            </div>

        </div>
        """


    # ------------------------------------------------ revisión de cambios por hilo
    # Filas: dicts con row_number, serie, accion y motivo (ver review/).

    @staticmethod
    def _tabla_filas_hilo(filas, con_motivo: bool):
        from html import escape

        celdas = "".join(
            "<tr>"
            f"<td style='padding:4px 10px;border-top:1px solid #d0d7de;'>{escape(str(f.get('row_number') or '-'))}</td>"
            f"<td style='padding:4px 10px;border-top:1px solid #d0d7de;'>{escape(str(f.get('serie') or '-'))}</td>"
            f"<td style='padding:4px 10px;border-top:1px solid #d0d7de;'>{escape(str(f.get('accion') or '-'))}</td>"
            + (
                f"<td style='padding:4px 10px;border-top:1px solid #d0d7de;'>{escape(str(f.get('motivo') or '-'))}</td>"
                if con_motivo else ""
            )
            + "</tr>"
            for f in filas
        )
        encabezado = (
            "<th style='padding:4px 10px;text-align:left;'>Fila</th>"
            "<th style='padding:4px 10px;text-align:left;'>Serie</th>"
            "<th style='padding:4px 10px;text-align:left;'>Acción</th>"
            + ("<th style='padding:4px 10px;text-align:left;'>Motivo</th>" if con_motivo else "")
        )
        return f"""
            <table style="border-collapse:collapse;margin-top:10px;font-size:13px;">
                <tr style="color:#57606a;">{encabezado}</tr>
                {celdas}
            </table>
        """

    def msj_revision_repare(self, request_code: str, filas):
        """Aviso a REPARE: filas de un mensaje de hilo que NO se aplicaron
        y requieren revisión humana."""
        from html import escape

        tabla = self._tabla_filas_hilo(filas, con_motivo=True)

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

                <div style="
                    font-size: 14px;
                    font-weight: bold;
                    margin-bottom: 12px;
                ">
                    REVIEW REQUIRED · {escape(str(request_code))}
                </div>

                <div style="color: #57606a;">
                    Este mensaje pide cambios sobre filas que no están
                    pendientes. No se aplicaron: cada fila <b>requiere revisión</b>.
                </div>

                {tabla}

            </div>

        </div>
        """

    def msj_cambios_hilo(self, request_code: str, aplicadas, revision, sin_cambios=()):
        """Respuesta al mensaje del hilo: qué se aplicó y qué quedó en revisión."""
        from html import escape

        if aplicadas:
            bloque_aplicadas = (
                "<div style='margin-top:12px;'><b>Aplicado</b></div>"
                + self._tabla_filas_hilo(aplicadas, con_motivo=False)
            )
        else:
            bloque_aplicadas = "<div style='margin-top:12px;color:#57606a;'>No se aplicó ningún cambio.</div>"

        if revision:
            bloque_revision = (
                "<div style='margin-top:16px;'><b>En revisión</b> (requiere revisión de REPARE)</div>"
                + self._tabla_filas_hilo(revision, con_motivo=True)
            )
        else:
            bloque_revision = ""

        if sin_cambios:
            bloque_sin_cambios = (
                "<div style='margin-top:16px;'><b>Sin cambios</b></div>"
                + self._tabla_filas_hilo(sin_cambios, con_motivo=True)
            )
        else:
            bloque_sin_cambios = ""

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

                <div style="
                    font-size: 14px;
                    font-weight: bold;
                    margin-bottom: 12px;
                ">
                    REQUEST UPDATED · {escape(str(request_code))}
                </div>

                <div style="color: #57606a;">
                    Se procesaron los cambios de este mensaje.
                </div>

                {bloque_aplicadas}
                {bloque_revision}
                {bloque_sin_cambios}

            </div>

        </div>
        """


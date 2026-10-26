import time

from parsers.danone_parse.process_data import DANONE_PROCESS
from parsers.danone_parse.utils import DANONE_UTILS
from parsers.danone_parse.reader import DANONE_READER
from parsers.danone_parse.catalog import DANONE_CATALOG
from parsers.danone_parse.business import DANONE_BUSINESS
from parsers.danone_parse.sabana import DANONE_SABANA
from config.config_general.messages import MENSAJES_REPARE
from src.excel_ingestion import Excel_Ingestion

from repository.danone.consultas_postgre import DB_POSTGRE
from bot import commands as bot_commands
from bot.perfiles import perfil_danone


from parsers.core.modelos import aviso_modelos, agregar_aviso
import os
from dotenv import load_dotenv


load_dotenv()

DEBUG = os.getenv("DEBUG", "false").strip().lower() == "true"

# process = DANONE_PARSE()
utils = DANONE_UTILS()
reader=DANONE_READER()
excel_ingestion = Excel_Ingestion()
msj = MENSAJES_REPARE()
db = DB_POSTGRE()


class DANONE_INIT :

    def __init__(self, duckConn):
        
        self.duckConn = duckConn
        self.process  = DANONE_PROCESS(self.duckConn)
        self.business = DANONE_BUSINESS(self.duckConn)
        self.catalog  = DANONE_CATALOG(self.duckConn)
        self.sabana   = DANONE_SABANA(self.duckConn)



    async def parse(self, client, user_id, mail_id, mail, customer):

        flujo = '[INIT]'

        
        proposito = (mail.unique_body.content or "")
        exist_email = db.email_init_exist(mail.id)


        if (exist_email) and (not DEBUG):
            print(f"{flujo}[ALERT]Correo Omitido por existencia")
            return None
        
        if not utils.analizar_proposito(proposito, mail.subject):
            print("[INFO] Email Sin Proposito Valido ")
            return None 
        
        try:
            archivos = await reader.get_adjuntos(
                client=client,
                user_id=user_id,
                mail_id=mail_id,
                duck_conn=self.duckConn,
            )
        except Exception:
            return None

        if not archivos:
            return None

        try:
            table = utils.unir_tablas(
                archivos,
                self.duckConn,
            )
        except Exception:
            return None


        count_item = self.duckConn.execute(
            f'SELECT COUNT(*) FROM "{table}"'
        ).fetchone()[0]
        if count_item < 1:
            print(f"[{flujo}] No hay elementos en la tabla: {table}")
            return {
                "mensaje": msj.formato_desconocido(),
                "attachments": None,
            }

        try:

            #reglas de negocio pre creacion
            missing_columns, rejected = self.business.business_rules_pre_creation(table)

            print(f"[PRE CREATION] columnas faltantes: {missing_columns}")

        except Exception as e:

            print(f"Error: {e}")
            return None

        if missing_columns:
            return {
                        "mensaje": msj.formato_desconocido(),
                        "attachments": None,
                    }
        count_files = self.duckConn.execute(f"""
            SELECT COUNT(*)
            FROM {table}
        """).fetchone()[0]

        # print(count_files)
        
        if count_files:

            self.catalog.calcula_coordenadas(table)
            self.catalog.calcula_distribuidora(table)
            self.catalog.calcula_modelo(table)   #proximamente

            self.sabana.fill_pre_template(table)
            self.sabana.fill_template(table)

        try:

            self.sabana.fill_form_solicitud(table)

        except Exception as e:

            return {
                        "mensaje": msj.formato_desconocido(),
                        "attachments": None,
                    }

        # else:
        #     #todos malos
        #     print("Todos los registros fueron malos")
        
        
        email_model = self.process.fill_email_model(mail, customer)

        request_code = db.save_email_log_init(email_model)

        link_email = mail.web_link

        parametros = self.process.prepare_data_request(
            request_code,
            customer,
            mail,
        )


        db.send_email_request(parametros)
        
        coolers = self.process.prepare_data_cooler(request_code)

        # print(f"[INFO] coolers: {coolers}")
        
        for cooler in coolers:
            db.send_email_coolers(cooler)

        attachments = [
            excel_ingestion.get_excelv2_attachment(
                self.duckConn,
                "sabana_movimiento",
                request_code,
            ),
            excel_ingestion.get_excelv2_attachment(
                self.duckConn,
                "sabana_ruta",
                request_code,
            ),
            # excel_ingestion.get_excelv2_attachment(
            #     self.duckConn,
            #     "solicitud",
            #     request_code,
            # ),
        ]

        attachments = [a for a in attachments if a is not None]

        temporary_files = await reader.download_original_files(
            client,
            user_id,
            mail_id,
        )
        utils.mark_rejected_original_files(self.duckConn, temporary_files)


        if attachments or temporary_files:
            return {
                "mensaje": agregar_aviso(msj.msj_send_presabana(request_code, link_email), aviso_modelos(self.duckConn, table)),
                "attachments": attachments,
                "temporary_files": temporary_files,
            }

        return None



class DANONE_REPLY:
    def __init__(self, duckConn):
        
        self.duckConn = duckConn
        self.process  = DANONE_PROCESS(self.duckConn)
        self.business = DANONE_BUSINESS(self.duckConn)
        self.catalog  = DANONE_CATALOG(self.duckConn)
        self.sabana   = DANONE_SABANA(self.duckConn)

    async def parse(
            self, 
            client, 
            user_id, 
            mail_id, 
            mail, 
            direccion, 
            customer = 'danone',
            customer_host = 'cliente.danone@repare.com.mx'
        ):

        flujo = '[REPLY]'

        reply = db.email_reply_validate(
            conversation_id=mail.conversation_id,
            subject=mail.subject,
        )

        if reply is None:
            # print("[INFO] =================== CORREO NUEVO ====================")
            return None

        request_code = reply["request_code"]
        link_email = reply["link_email"]

        result_type = await reader.detectar_tipo_correo(
            client=client,
            user_id=user_id,
            mail_id=mail_id,
            email=mail,
        )

        # if DEBUG == "True":
        #     print(result_type)

        # ==========================================================
        # CLIENTE -> REPARE
        # Solo acepta Excel
        # ==========================================================
        if direccion == "inbound":

            sender = (
                getattr(mail.sender, "email_address", None).address
                if getattr(mail.sender, "email_address", None)
                else ""
            ).lower()
            
            es_repare = sender == customer_host


            if not result_type["tiene_excel"]:
                return None

            try:
                archivos = await reader.get_adjuntos(
                    client=client,
                    user_id=user_id,
                    mail_id=mail_id,
                    duck_conn=self.duckConn,
                )

            except Exception:
                return None

            if not archivos:
                return None

            table = utils.unir_tablas(
                archivos,
                self.duckConn,
            )

            count_item = self.duckConn.execute(
                f'SELECT COUNT(*) FROM "{table}"'
            ).fetchone()[0]
            if count_item < 1:
                print(f"[{flujo}] No hay elementos en la tabla: {table}")
                return {
                    "mensaje": msj.formato_desconocido(),
                    "attachments": None,
                }

            if es_repare:
                return None

            else:
 
                missing_columns, rejected = self.business.business_rules_pre_creation(table)
 
                if missing_columns:
                    return None

                self.catalog.calcula_coordenadas(table)
                self.catalog.calcula_distribuidora(table)
                self.catalog.calcula_modelo(table)


 
                self.sabana.fill_pre_template(table)
           
                self.sabana.fill_template(table)
       
                self.sabana.fill_form_solicitud(table)
 
                # request_code = self.process.prepare_cooler_update(archivos[0]["table"])
       
                # db.cancel_pending_coolers(request_code)
       
                coolers = self.process.prepare_data_cooler(request_code)
       
                for cooler in coolers:
                    db.insert_update_cooler(cooler)

                #actualizar email_request
                db.update_email_request(request_code)
                result_status = db.get_email_request_status(request_code)
       
                attachments = [
                    excel_ingestion.get_excelv2_attachment(
                        self.duckConn,
                        "sabana_movimiento",
                        request_code,
                    ),
                    excel_ingestion.get_excelv2_attachment(
                        self.duckConn,
                        "sabana_ruta",
                        request_code,
                    ),
                    # excel_ingestion.get_excelv2_attachment(
                    #     self.duckConn,
                    #     "solicitud",
                    #     request_code,
                    # ),
                ]
       
                attachments = [a for a in attachments if a is not None]

                temporary_files = await reader.download_original_files(
                    client,
                    user_id,
                    mail_id,
                )
       
                if attachments or temporary_files:
                    return {
                        "mensaje": agregar_aviso(msj.msj_add_cliente(request_code, link_email), aviso_modelos(self.duckConn, table)),
                        "attachments": attachments,
                        "temporary_files": temporary_files,
                    }
                return None

            
        # ==========================================================
        # REPARE -> CLIENTE
        # Puede ser Excel o palabra reservada, nunca ambos
        # ==========================================================
        elif direccion == "outbound":
 
            if result_type["tiene_excel"] and result_type["tiene_palabra_reservada"]:
                return None

            if result_type["tiene_excel"]:
                try:
                    archivos = await reader.get_adjuntos(
                        client=client,
                        user_id=user_id,
                        mail_id=mail_id,
                        duck_conn=self.duckConn,
                    )

                except Exception:
                    return None

                if not archivos:
                    return None

                table = utils.unir_tablas(
                    archivos,
                    self.duckConn,
                )

                upd_coolers = self.process.prepare_cooler_update(archivos[0]["table"])
                db.update_cooler(request_code,upd_coolers)

                db.update_email_request(request_code)
                result_status = db.get_email_request_status(request_code)

                request = db.get_total_coolers(request_code)

                request_total = request[0]["total_coolers"]
                request_completed = request[0]["completed_coolers"]
                request_pending = request[0]["pending_coolers"]
                request_failed = request[0]["failed_coolers"]


                if result_status == 'COMPLETED':

                    mensaje_final = msj.msj_solicitud_completa_esc1(
                            request_code,
                            url=mail.web_link,
                            total=request_total,
                            con_os=request_completed,
                            sin_os=request_pending,
                            
                        )
                    return {
                                "mensaje": mensaje_final,
                                "attachments": None,
                            }
                
                elif result_status == 'IN_PROGRESS':
                    mensaje_final = msj.msj_cambios(
                        request_code,
                        url=mail.web_link,
                        total=request_total,
                        con_os=request_completed,
                        sin_os=request_pending,
                        desconocidos=request_failed
                    )
                    return {
                            "mensaje": mensaje_final,
                            "attachments": None,
                        }
                
                else:
                    mensaje_final = msj.msj_cambios(
                                            request_code,
                                            url=mail.web_link,
                                            total=request_total,
                                            con_os=request_completed,
                                            sin_os=request_pending,
                                            desconocidos=request_failed
                                        )
                    

                    return {
                        "mensaje": mensaje_final,
                        "attachments": None,
                    }

        elif direccion == "reply_to_bot":
            return await bot_commands.ejecutar(
                perfil_danone(db, msj, self.process),
                result_type,
                bot_commands.solicitud_fija(request_code),
            )


        # ==========================================================
        # BOT
        # ==========================================================
        else:
            print("es un robot detenganlo")
            return None

from config.customers.penafiel.movimientos_penafiel import DIC_SABANAS_MOV
from parsers.penafiel_parse.utils import PENAFIEL_UTILS
from pathlib import Path

utils = PENAFIEL_UTILS()

class PENAFIEL_SABANA:


    def __init__(self, duckConn):
        self.duckConn = duckConn

    def _col_opcional(self, table, columna, default):
        # Columna extra del Excel: si no existe en la tabla, usa el default.
        existentes = {
            fila[0] for fila in self.duckConn.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = ?",
                [table],
            ).fetchall()
        }

        if columna not in existentes:
            return f"'{default}'"

        return (
            f"COALESCE(NULLIF(TRIM(CAST(\"{columna}\" AS VARCHAR)), ''), '{default}')"
        )

    def fill_form_solicitud(self, table):

        # Verificar si la tabla de entrada tiene la columna CBU
        columns = self.duckConn.execute(f"""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = '{table}'
        """).fetchdf()["column_name"].tolist()

        # Si el Excel no trae CBU, crearla vacía
        if "CBU" not in columns:
            self.duckConn.execute(f'''
                ALTER TABLE "{table}"
                ADD COLUMN "CBU" VARCHAR
            ''')

        self.make_sabanas(
            "config/config_general/querys/form_solicitud.sql"
        )
        
        self.duckConn.execute(f"""
            INSERT INTO solicitud (
                "ID CLIENTE",
                "FECHA DE SOLICITUD",
                "MODELO",
                "SERIE FABRICANTE",
                "SERIE",
                "TIPO DE SERVICIO",
                "CANAL",
                "REGION",
                "PLAZA",
                "RAZON SOCIAL",
                "DIRECCION",
                "CP",
                "CIUDAD",
                "COLONIA",
                "LATITUD",
                "LONGITUD",
                "RUTA",
                "TELEFONO 1",
                "TELEFONO 2",
                "COMENTARIOS",
                "CBU",
                "OS"
            )

            SELECT
                "ID CLIENTE",
                "FECHA DE SOLICITUD",
                "MODELO",
                "SERIE FABRICANTE",
                "SERIE",
                "TIPO DE SERVICIO",
                "CANAL",
                "REGION",
                "PLAZA",
                "RAZON SOCIAL",
                "DIRECCION",
                "CP",
                "CIUDAD",
                "COLONIA",
                "LATITUD",
                "LONGITUD",
                "RUTA",
                "TELEFONO 1",
                "TELEFONO 2",
                "COMENTARIOS",
                "CBU",
                NULL AS "OS"
            FROM "{table}"

            UNION ALL

            SELECT
                "ID CLIENTE",
                "FECHA DE SOLICITUD",
                "MODELO",
                "SERIE FABRICANTE",
                "SERIE",
                "TIPO DE SERVICIO",
                "CANAL",
                "REGION",
                "PLAZA",
                "RAZON SOCIAL",
                "DIRECCION",
                "CP",
                "CIUDAD",
                "COLONIA",
                "LATITUD",
                "LONGITUD",
                "RUTA",
                "TELEFONO 1",
                "TELEFONO 2",
                "COMENTARIOS",
                "CBU",
                "OS"
            FROM solicitudes_rechazadas
        """)



    def fill_pre_template(self, table):

        self.make_sabanas(
            "config/config_general/querys/generic_presabana.sql"
        )

        self.fill_pre_sabana(table)



    def fill_template(self, table):

            types_services = utils.distinct_type_service(table,self.duckConn)

            if any(service in DIC_SABANAS_MOV["MOVIMIENTOS"] for service in types_services):

                self.make_sabanas(
                    "config/config_general/querys/generic_sabana_movimientos.sql"
                )

                self.fill_movimiento(table)



            if any(service in DIC_SABANAS_MOV["RUTA"] for service in types_services):

                self.make_sabanas(
                    "config/config_general/querys/generic_sabana_ruta.sql"
                )

                self.fill_ruta(table)


    def make_sabanas(self, ruta_sabana):

        query = Path(
            ruta_sabana
        ).read_text(encoding="utf-8")

        #creamos sabanas
        self.duckConn.execute(query)

    def fill_pre_sabana(self,table):
            print(f"[DEBUG] Columnas de {table}:", self.duckConn.execute(f'SELECT * FROM "{table}" LIMIT 0').fetchdf().columns.tolist())
            calle = self._col_opcional(table, "CALLE", "NP")
            entre_calle1 = self._col_opcional(table, "ENTRE CALLE", "NP")
            entre_calle2 = self._col_opcional(table, "Y CALLE", "NP") 
            canal = self._col_opcional(table, "CANAL", "Sin Canal")
            horario_atencion = self._col_opcional(table, "HORARIO_ATENCION", "")
            responsable = self._col_opcional(table, "RESPONSABLE", "")
            numero = self._col_opcional(table, "NUMERO", "")
            correo = self._col_opcional(table, "CORREO", "")


            # values = ", ".join(f"'{v}'" for v in DIC_SABANAS_MOV["MOVIMIENTOS"])
            # print("[DEBUG] Valores de tipo de servicio para pre_sabana: ", values)

            self.duckConn.execute(f"""
                INSERT INTO pre_sabana (
                    Distribuidora,
                    Categoria,
                    Linea,
                    Modelo,
                    Numero_Activo,
                    Serie,        
                    Numero_Puertas,
                    Imagen,
                    Canal,
                    Hora_Atencion, 
                    Observaciones,
                    Tipo_Servicio,
                    Id_Servicio,
                    Tipo_Actividad,
                    Actividad,
                    Datos_Prospeccion,
                    Tipo_Orden,
                    Numero_Cliente,
                    Nombre_PDV,
                    Calle,
                    Numero,
                    Entre_Calle1,
                    Entre_Calle2,
                    Colonia,
                    Municipio,
                    Codigo_Postal,
                    Telefono_Fax,
                    Nombre_Contacto_PDV,
                    Correo_Electronico,
                    Latitud,
                    Longitud,
                    Distribuidora_Puesto_Trabajo,
                    Cp_Generado,
                    Colonia_Generado,
                    Ciudad_Generado,
                    Estado_Generado,
                    Pais_Generado 
                )
                SELECT
                    COALESCE("DISTRIBUIDORA_GEN",'') as Distribuidora,
                    "CATEGORIA_GEN" as Categoria,
                    "LINEA_GEN" as Linea,
                    "MODELO_GEN" as Modelo,
                    "SERIE FABRICANTE"  as Numero_Activo,
                    "SERIE" as Serie,
                    '' as Numero_Puertas,
                    '' as Imagen,
                    {canal} as Canal,
                    {horario_atencion} as Hora_Atencion,

                    COALESCE("TIPO DE SERVICIO", '') || ' / ' ||
                    COALESCE(COMENTARIOS, '') || ' /Region: ' ||
                    COALESCE(CAST(REGION AS VARCHAR), '') || ' /Canal: ' ||
                    COALESCE(CANAL, '') || ' /Ruta: ' ||
                    COALESCE(CAST(RUTA AS VARCHAR), '') AS Observaciones,

                    '' as Tipo_Servicio,
                    '' as Id_Servicio,
                    '' as Tipo_Actividad,
                    '' as Actividad,

                    'NA' as Datos_Prospeccion,
                    '' as Tipo_Orden,
                    "ID CLIENTE" as Numero_Cliente,
                    "RAZON SOCIAL" as Nombre_PDV,
                    {calle} as Calle,
                    {numero} as Numero,
                    {entre_calle1} as Entre_Calle1,
                    {entre_calle2} as Entre_Calle2,
                    "COLONIA" as Colonia,
                    CIUDAD as Municipio,
                    CP as Codigo_Postal,
                    "TELEFONO 2" as Telefono_Fax,
                    {responsable} as Nombre_Contacto_PDV,
                    {correo} as Correo_Electronico,
                    LATITUD as Latitud,
                    LONGITUD as Longitud,
                    "DISTRIBUIDORA_GEN" as Distribuidora_Puesto_Trabajo,
                    
                    CP_GEN AS "Cp_Generado",
                    COLONIA_GEN AS "Colonia_Generado", 
                    CIUDAD_GEN AS "Ciudad_Generado",
                    ESTADO_GEN AS "Estado_Generado",
                    PAIS_GEN AS "Pais_Generado"
                FROM {table}


            """)


    def fill_movimiento(self,table):
            print(f"[DEBUG] Columnas de {table}:", self.duckConn.execute(f'SELECT * FROM "{table}" LIMIT 0').fetchdf().columns.tolist())
            calle = self._col_opcional(table, "CALLE", "NP")
            canal = self._col_opcional(table, "CANAL", "Sin Canal")
            horario_atencion = self._col_opcional(table, "HORARIO_ATENCION", "")
            responsable = self._col_opcional(table, "RESPONSABLE", "")
            correo = self._col_opcional(table, "CORREO", "")
            numero = self._col_opcional(table, "NUMERO", "")
            entre_calle1 = self._col_opcional(table, "ENTRE CALLE", "NP")
            entre_calle2 = self._col_opcional(table, "Y CALLE", "NP")
            values = ", ".join(f"'{v}'" for v in DIC_SABANAS_MOV["MOVIMIENTOS"])

            self.duckConn.execute(f"""
                INSERT INTO sabana_movimiento (
                    Distribuidora,
                    Categoria,
                    Linea,
                    Modelo,
                    Numero_Activo,
                    Serie,        
                    Numero_Puertas,
                    Imagen,
                    Canal,
                    Hora_Atencion, 
                    Observaciones,
                    Tipo_Servicio,
                    Id_Servicio,
                    Tipo_Actividad,
                    Actividad,
                    Datos_Prospeccion,
                    Tipo_Orden,
                    Numero_Cliente,
                    Nombre_PDV,
                    Calle,
                    Numero,
                    Entre_Calle1,
                    Entre_Calle2,
                    Colonia,
                    Municipio,
                    Codigo_Postal,
                    Telefono_Fax,
                    Nombre_Contacto_PDV,
                    Correo_Electronico,
                    Latitud,
                    Longitud,
                    Distribuidora_Puesto_Trabajo,
                    Cp_Generado,
                    Colonia_Generado,
                    Ciudad_Generado,
                    Estado_Generado,
                    Pais_Generado 
                )
                SELECT
                    COALESCE("DISTRIBUIDORA_GEN",'') as Distribuidora,
                    "CATEGORIA_GEN" as Categoria,
                    "LINEA_GEN" as Linea,
                    COALESCE("MODELO_GEN", "MODELO") as Modelo,
                    "SERIE FABRICANTE"  as Numero_Activo,
                    "SERIE" as Serie,
                    '' as Numero_Puertas,
                    '' as Imagen,
                    {canal} as Canal,
                    {horario_atencion} as Hora_Atencion,

                    COALESCE("TIPO DE SERVICIO", '') || ' / ' ||
                    COALESCE(COMENTARIOS, '') || ' /Region: ' ||
                    COALESCE(CAST(REGION AS VARCHAR), '') || ' /Canal: ' ||
                    COALESCE(CANAL, '') || ' /Ruta: ' ||
                    COALESCE(CAST(RUTA AS VARCHAR), '') AS Observaciones,

                    '' as Tipo_Servicio,
                    '' as Id_Servicio,
                    '' as Tipo_Actividad,
                    '' as Actividad,

                    'NA' as Datos_Prospeccion,
                    '' as Tipo_Orden,
                    "ID CLIENTE" as Numero_Cliente,
                    "RAZON SOCIAL" as Nombre_PDV,
                    {calle} as Calle,
                    {numero} as Numero,
                    {entre_calle1} as Entre_Calle1,
                    {entre_calle2} as Entre_Calle2,
                    "COLONIA" as Colonia,
                    CIUDAD as Municipio,
                    CP as Codigo_Postal,
                    "TELEFONO 1" as Telefono_Fax,
                    {responsable} as Nombre_Contacto_PDV,
                    {correo} as Correo_Electronico,
                    LATITUD as Latitud,
                    LONGITUD as Longitud,
                    "DISTRIBUIDORA_GEN" as Distribuidora_Puesto_Trabajo,

                    CP_GEN AS "Cp_Generado",
                    COLONIA_GEN AS "Colonia_Generado", 
                    CIUDAD_GEN AS "Ciudad_Generado",
                    ESTADO_GEN AS "Estado_Generado",
                    PAIS_GEN AS "Pais_Generado"
                FROM {table}
            WHERE

                "TIPO DE SERVICIO"  in ({values})

            """)



    def fill_ruta(self,table):
        calle = self._col_opcional(table, "CALLE", "")
        numero = self._col_opcional(table, "NUMERO", "")
        entre_calle1 = self._col_opcional(table, "ENTRE CALLE", "")
        entre_calle2 = self._col_opcional(table, "Y CALLE", "")
        canal = self._col_opcional(table, "CANAL", "Sin Canal")
        horario_atencion = self._col_opcional(table, "HORARIO_ATENCION", "")
        responsable = self._col_opcional(table, "RESPONSABLE", "")
        correo = self._col_opcional(table, "CORREO", "")
        values = ", ".join(f"'{v}'" for v in DIC_SABANAS_MOV["RUTA"])

        self.duckConn.execute(f"""
            INSERT INTO sabana_ruta (
                Distribuidora,
                Categoria,
                Linea,
                Modelo,
                Numero_Activo,
                Serie,
                Observaciones,
                Hora_Atencion,
                Prioridad,
                Folio,
                Ticket_Solicitud,
                Canal,
                Correo_Electronico_1,
                Numero_Cliente,
                Nombre_PDV,
                Calle,
                Numero,
                Entre_Calle1,
                Entre_Calle2,
                Colonia,
                Municipio,
                Codigo_Postal,
                Latitud,
                Longitud,
                Telefono_Fax_1,
                Telefono_Fax_2,
                Correo_Electronico_2,
                Nombre_Contacto_PDV,
                Cp_Generado,
                Colonia_Generado,
                Ciudad_Generado,
                Estado_Generado,
                Pais_Generado 
            )
            SELECT

                COALESCE("DISTRIBUIDORA_GEN",'') as Distribuidora,
                "CATEGORIA_GEN" as Categoria,
                "LINEA_GEN" as Linea,
                COALESCE("MODELO_GEN", "MODELO") as Modelo,
                "SERIE FABRICANTE"  as Numero_Activo,
                "SERIE" as Serie,

                COALESCE("TIPO DE SERVICIO", '') || ' / ' ||
                COALESCE(COMENTARIOS, '') || ' /Region: ' ||
                COALESCE(CAST(REGION AS VARCHAR), '') || ' /Canal: ' ||
                COALESCE(CANAL, '') || ' /Ruta: ' ||
                COALESCE(CAST(RUTA AS VARCHAR), '') AS Observaciones,

                {horario_atencion} as Hora_Atencion,
                '' as Prioridad,
                '' as Folio,
                '' as Ticket_Solicitud,
                {canal} as Canal,
                {correo} as Correo_Electronico_1,
                "ID CLIENTE" as Numero_Cliente,
                "RAZON SOCIAL" as Nombre_PDV,
                {calle} as Calle,
                {numero} as Numero, 
                {entre_calle1} as Entre_Calle1,
                {entre_calle2} as Entre_Calle2,
                COLONIA as Colonia,
                CIUDAD as Municipio,
                CP as Codigo_Postal,
                LATITUD as Latitud,
                LONGITUD as Longitud,
                "TELEFONO 1" as Telefono_Fax_1,
                "TELEFONO 2" as Telefono_Fax_2,
                '' as Correo_Electronico_2,
                {responsable} as Nombre_Contacto_PDV,

                CP_GEN AS "Cp_Generado",
                COLONIA_GEN AS "Colonia_Generado", 
                CIUDAD_GEN AS "Ciudad_Generado",
                ESTADO_GEN AS "Estado_Generado",
                PAIS_GEN AS "Pais_Generado"


            FROM {table}

            WHERE

                "TIPO DE SERVICIO"  in ({values})
        """)
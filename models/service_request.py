from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class Template_Sabana(BaseModel):

    Distribuidora: Optional[str] = None
    Categoria: Optional[str] = None
    Linea: Optional[str] = None
    Modelo: Optional[str] = None
    Numero_Activo: Optional[str] = None
    Serie: Optional[str] = None
    Comentarios_Cliente: Optional[str] = None
    Hora_Atencion: Optional[str] = None
    Prioridad: Optional[str] = None
    Folio: Optional[str] = None
    Ticket_Solicitud: Optional[str] = None
    Canal: Optional[str] = None
    Correo_Solicitante: Optional[str] = None
    Numero_Cliente: Optional[str] = None
    Nombre_PDV: Optional[str] = None
    Calle: Optional[str] = None
    Numero: Optional[str] = None
    Entre_Calle1: Optional[str] = None
    Entre_Calle2: Optional[str] = None
    Colonia: Optional[str] = None
    Municipio: Optional[str] = None
    Codigo_Postal: Optional[str] = None
    Latitud: Optional[str] = None
    Longitud: Optional[str] = None
    Telefono_Fax: Optional[str] = None
    Correo_Electronico: Optional[str] = None
    Nombre_Contacto_PDV: Optional[str] = None
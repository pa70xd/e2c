FAILS_RESPONSE = {
    "proposito_01": (
        "No fue posible identificar un propósito válido en el contenido del correo. "
        "Verifique que la solicitud contenga información suficiente para determinar el tipo de servicio requerido."
    ),

    "adjuntos_01": (
        "No fue posible identificar un documento adjunto válido o con las propiedades correspondientes a una solicitud. "
        "Verifique que la solicitud contenga la información requerida."
    ),

    "adjuntos_02": (
        "Ocurrió un error al obtener o procesar los archivos adjuntos del correo. "
        "Verifique que los archivos sean accesibles y que tengan un formato compatible."
    ),

    "tableau_01": (
        "Ocurrió un error al consultar la información del catálogo de modelos en Tableau. "
        "Verifique la disponibilidad del servicio y la información proporcionada."
    ),

    "business_01": (
        "Ocurrió un error durante la ejecución de las reglas de negocio. "
        "Verifique la consistencia de la información de la solicitud e intente nuevamente."
    ),
    "fill_model_01":(
        "Ocurrio un problema al momento de rellenar el modelo init para carga de solicitud de servicio"
    )
}
def get_fail_response(indice: str) -> dict:
    return {
        "status": "ERROR",
        "code": indice,
        "message": FAILS_RESPONSE.get(indice, "Error desconocido."),
    }
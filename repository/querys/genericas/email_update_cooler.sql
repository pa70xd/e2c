UPDATE {cooler_request_table}
SET
    id_cliente = %s,
    fecha_solicitud = %s,
    modelo = %s,
    serie_fabricante = %s,
    serie_dnn_bnf = %s,
    tipo_servicio = %s,
    canal = %s,
    region = %s,
    plaza = %s,
    razon_social = %s,
    direccion = %s,
    cp = %s,
    ciudad = %s,
    colonia = %s,
    latitud = %s,
    longitud = %s,
    ruta = %s,
    telefono_1 = %s,
    telefono_2 = %s,
    comentarios = %s,
    cbu = %s,
    cliente = %s,
    os = %s,

    status = %s,
    rejection_reason = %s,
    prioridad = %s,
    folio = %s,
    ticket_solicitud = %s,
    assigned_to = %s,
    gestion_observaciones = %s,
    fecha_asignacion = %s,
    fecha_atencion = %s,
    fecha_completado = %s,

    updated_at = CURRENT_TIMESTAMP AT TIME ZONE 'America/Mexico_City'

WHERE request_code = %s
  AND row_number = %s
  AND status = 'PENDING';
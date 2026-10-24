INSERT INTO {cooler_request_table} (
    request_code,
    row_number,

    id_cliente,
    fecha_solicitud,
    modelo,
    serie_fabricante,
    serie_dnn_bnf,
    tipo_servicio,
    canal,
    region,
    plaza,
    razon_social,
    direccion,
    cp,
    ciudad,
    colonia,
    latitud,
    longitud,
    ruta,
    telefono_1,
    telefono_2,
    comentarios,
    cbu,
    cliente,
    os,

    status,
    rejection_reason,
    prioridad,
    folio,
    ticket_solicitud,
    assigned_to,
    gestion_observaciones,
    fecha_asignacion,
    fecha_atencion,
    fecha_completado,

    created_at,
    updated_at

)
SELECT
    %s, -- request_code
    %s, -- row_number

    %s, -- id_cliente
    %s, -- fecha_solicitud
    %s, -- modelo
    %s, -- serie_fabricante
    %s, -- serie_dnn_bnf
    %s, -- tipo_servicio
    %s, -- canal
    %s, -- region
    %s, -- plaza
    %s, -- razon_social
    %s, -- direccion
    %s, -- cp
    %s, -- ciudad
    %s, -- colonia
    %s, -- latitud
    %s, -- longitud
    %s, -- ruta
    %s, -- telefono_1
    %s, -- telefono_2
    %s, -- comentarios
    %s, -- cbu
    %s, -- cliente
    %s, -- os

    %s, -- status
    %s, -- rejection_reason
    %s, -- prioridad
    %s, -- folio
    %s, -- ticket_solicitud
    %s, -- assigned_to
    %s, -- gestion_observaciones
    %s, -- fecha_asignacion
    %s, -- fecha_atencion
    %s, -- fecha_completado

    CURRENT_TIMESTAMP AT TIME ZONE 'America/Mexico_City',
    CURRENT_TIMESTAMP AT TIME ZONE 'America/Mexico_City'
  
WHERE NOT EXISTS (
    SELECT 1
    FROM {cooler_request_table} c
    WHERE request_code = %s
      AND COALESCE(c.serie_fabricante, '') = COALESCE(%s, '')
      AND COALESCE(c.serie_dnn_bnf, '') = COALESCE(%s, '')
);
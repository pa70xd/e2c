-- Un caso de Holanda en cooler_request (mapeo en consultas_postgre.py).
-- WHERE NOT EXISTS global por folio (= CASO2): cada correo de Holanda tiene
-- su propio request_code, así que la llave para no duplicar es el caso.
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

    %s, -- id_cliente        <- SAP
    %s, -- fecha_solicitud   <- Fecha
    %s, -- modelo            <- Modelo
    %s, -- serie_fabricante  <- Serie
    %s, -- serie_dnn_bnf     <- Congelador (slot reutilizado, no aplica en Danone)
    %s, -- tipo_servicio     <- Tipo de queja
    %s, -- canal             <- Canal
    %s, -- region            <- Region
    %s, -- plaza             <- Agencia
    %s, -- razon_social      <- Nombre Negocio
    %s, -- direccion         <- Calle y numero
    %s, -- cp                <- CP
    %s, -- ciudad            <- Municipio
    %s, -- colonia           <- Colonia
    %s, -- latitud
    %s, -- longitud
    %s, -- ruta
    %s, -- telefono_1        <- Telefono
    NULL, -- telefono_2 (Holanda no trae un segundo teléfono)
    %s, -- comentarios       <- Clasificador de caso
    %s, -- cbu               <- Origen (HELADIO/GDR)
    '{cliente}', -- cliente
    %s, -- os                <- OS/estatus (incluye MARCA_DUPLICADO si aplica)

    'PENDING', -- status
    NULL, -- rejection_reason
    'MEDIA', -- prioridad
    %s, -- folio             <- Caso2 (llave de negocio real de Holanda)
    %s, -- ticket_solicitud  <- TE (se guarda si viene; puede ser NULL)
    NULL, -- assigned_to
    %s, -- gestion_observaciones (bundle: Nombre del cliente, Estado, Segmento,
        --   Agrupador, Agencia Satelite, Oxxo, Sin SAP/Sin Congelador, Proveedor
        --   -- campos de Holanda sin columna propia en el esquema compartido)
    NULL, -- fecha_asignacion
    NULL, -- fecha_atencion
    NULL, -- fecha_completado

    CURRENT_TIMESTAMP AT TIME ZONE 'America/Mexico_City',
    CURRENT_TIMESTAMP AT TIME ZONE 'America/Mexico_City'

WHERE NOT EXISTS (
    SELECT 1
    FROM {cooler_request_table} c
    WHERE c.cliente = '{cliente}'
      AND c.folio = %s
);

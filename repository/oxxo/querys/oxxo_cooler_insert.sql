-- Una OS de Oxxo en cooler_request (mapeo en consultas_postgre.py).
-- Dedupe: el mismo folio (ticket de mantenimiento o folio de garantía) no se
-- inserta dos veces, ni en el mismo cliente ni entre los dos buzones de Oxxo.
-- Sin folio (filas de Excel sin FOLIO) solo cuenta request_code + row_number.
INSERT INTO {cooler_request_table} (
    request_code,
    row_number,

    id_cliente,
    fecha_solicitud,
    modelo,
    serie_fabricante,
    tipo_servicio,
    region,
    plaza,
    razon_social,
    direccion,
    cp,
    ciudad,
    colonia,
    telefono_1,
    comentarios,
    cliente,

    status,
    prioridad,
    folio,
    ticket_solicitud,
    gestion_observaciones,

    created_at,
    updated_at
)
SELECT
    %s, -- request_code
    %s, -- row_number

    %s, -- id_cliente        <- CR de la tienda
    %s, -- fecha_solicitud
    %s, -- modelo
    %s, -- serie_fabricante
    %s, -- tipo_servicio     <- categoría (mantenimiento) / GARANTIA
    %s, -- region
    %s, -- plaza
    %s, -- razon_social      <- tienda
    %s, -- direccion
    %s, -- cp
    %s, -- ciudad
    %s, -- colonia
    %s, -- telefono_1
    %s, -- comentarios       <- falla / diagnóstico
    %s, -- cliente           <- OXXO u OXXO_GARANTIAS

    'PENDING', -- status
    %s, -- prioridad
    %s, -- folio             <- ticket (mantenimiento) o folio (garantía)
    %s, -- ticket_solicitud  <- folio de referencia de mantenimiento (garantía)
    %s, -- gestion_observaciones

    CURRENT_TIMESTAMP AT TIME ZONE 'America/Mexico_City',
    CURRENT_TIMESTAMP AT TIME ZONE 'America/Mexico_City'

WHERE NOT EXISTS (
    SELECT 1
    FROM {cooler_request_table} c
    WHERE c.request_code = %s
      AND c.row_number = %s
)
AND (
    %s::text IS NULL
    OR NOT EXISTS (
        SELECT 1
        FROM {cooler_request_table} c
        WHERE c.cliente IN ({clientes})
          AND c.folio = %s
    )
)
RETURNING request_code, row_number;

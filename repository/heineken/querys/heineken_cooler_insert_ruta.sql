-- Ruta: no inserta si ya existe el mismo ORDEN (folio); sin ORDEN, la misma serie en la solicitud.
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
    telefono_1,
    comentarios,
    cbu,
    os,
    folio,
    ticket_solicitud,
    gestion_observaciones,
    cliente,
    status,
    prioridad,
    created_at,
    updated_at
)
SELECT
    %(request_code)s,
    %(row_number)s,
    %(id_cliente)s,
    %(fecha_solicitud)s,
    %(modelo)s,
    %(serie_fabricante)s,
    %(serie_dnn_bnf)s,
    %(tipo_servicio)s,
    %(canal)s,
    %(region)s,
    %(plaza)s,
    %(razon_social)s,
    %(direccion)s,
    %(cp)s,
    %(ciudad)s,
    %(colonia)s,
    %(latitud)s,
    %(longitud)s,
    %(telefono_1)s,
    %(comentarios)s,
    %(cbu)s,
    %(os)s,
    %(folio)s,
    %(ticket_solicitud)s,
    %(gestion_observaciones)s,
    '{cliente}',
    'PENDING',
    'MEDIA',
    CURRENT_TIMESTAMP AT TIME ZONE 'America/Mexico_City',
    CURRENT_TIMESTAMP AT TIME ZONE 'America/Mexico_City'
WHERE NOT EXISTS (
    SELECT 1 FROM {cooler_request_table} c
    WHERE c.cliente = '{cliente}'
      AND (
        (CAST(%(folio)s AS TEXT) IS NOT NULL AND c.folio = %(folio)s)
        OR (CAST(%(folio)s AS TEXT) IS NULL
            AND c.request_code = %(request_code)s
            AND c.serie_fabricante = %(serie_fabricante)s)
      )
);

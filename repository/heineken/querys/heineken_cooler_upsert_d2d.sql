-- D2D: actualiza el caso de la misma solicitud y serie (reenvío) o lo inserta.
WITH actualizado AS (
    UPDATE {cooler_request_table}
    SET
        id_cliente = %(id_cliente)s,
        fecha_solicitud = %(fecha_solicitud)s,
        modelo = %(modelo)s,
        serie_fabricante = %(serie_fabricante)s,
        serie_dnn_bnf = %(serie_dnn_bnf)s,
        tipo_servicio = %(tipo_servicio)s,
        canal = %(canal)s,
        region = %(region)s,
        plaza = %(plaza)s,
        razon_social = %(razon_social)s,
        direccion = %(direccion)s,
        cp = %(cp)s,
        ciudad = %(ciudad)s,
        colonia = %(colonia)s,
        latitud = %(latitud)s,
        longitud = %(longitud)s,
        telefono_1 = %(telefono_1)s,
        comentarios = %(comentarios)s,
        cbu = %(cbu)s,
        os = %(os)s,
        folio = %(folio)s,
        ticket_solicitud = %(ticket_solicitud)s,
        gestion_observaciones = %(gestion_observaciones)s,
        status = 'PENDING',
        updated_at = CURRENT_TIMESTAMP AT TIME ZONE 'America/Mexico_City'
    WHERE cliente = '{cliente}'
      AND request_code = %(request_code)s
      AND serie_fabricante = %(serie_fabricante)s
      AND status <> 'CANCELLED'
    RETURNING 1
)
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
WHERE NOT EXISTS (SELECT 1 FROM actualizado)
  AND NOT EXISTS (
    SELECT 1 FROM {cooler_request_table} c
    WHERE c.cliente = '{cliente}'
      AND c.request_code = %(request_code)s
      AND c.serie_fabricante = %(serie_fabricante)s
  );

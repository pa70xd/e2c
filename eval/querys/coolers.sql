-- Solo lectura. Filas de las solicitudes pedidas. Sin direcciones, razón social ni teléfonos.
SELECT
    request_code,
    row_number,
    serie_fabricante,
    serie_dnn_bnf,
    os,
    status,
    created_at,
    updated_at
FROM {cooler_request_table}
WHERE request_code = ANY(%s)
ORDER BY request_code, row_number

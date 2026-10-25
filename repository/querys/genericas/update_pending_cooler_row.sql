UPDATE {cooler_request_table}
SET
    folio = COALESCE(NULLIF(TRIM(%s), ''), folio),
    serie_fabricante = COALESCE(NULLIF(TRIM(%s), ''), serie_fabricante),
    serie_dnn_bnf = COALESCE(NULLIF(TRIM(%s), ''), serie_dnn_bnf),
    modelo = COALESCE(NULLIF(TRIM(%s), ''), modelo),
    tipo_servicio = COALESCE(NULLIF(TRIM(%s), ''), tipo_servicio),
    direccion = COALESCE(NULLIF(TRIM(%s), ''), direccion),
    updated_at = CURRENT_TIMESTAMP AT TIME ZONE 'America/Mexico_City'
WHERE request_code = %s
  AND row_number = %s
  AND status = 'PENDING'
RETURNING request_code, row_number;

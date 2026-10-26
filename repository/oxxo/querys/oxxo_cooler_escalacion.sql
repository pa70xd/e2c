-- Marca la escalación en la fila (no cambia su status).
UPDATE {cooler_request_table}
SET
    gestion_observaciones = CONCAT_WS(' | ', NULLIF(gestion_observaciones, ''), %s),
    updated_at = CURRENT_TIMESTAMP AT TIME ZONE 'America/Mexico_City'
WHERE request_code = %s
  AND row_number = %s
RETURNING request_code, row_number;

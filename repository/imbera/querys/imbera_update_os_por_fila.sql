-- Outbound desde el TEXTO ("orden generada: <n>"): OS a una fila PENDING.
UPDATE {cooler_request_table}
SET
    os = %s,
    status = 'ACCEPTED',
    updated_at = CURRENT_TIMESTAMP AT TIME ZONE 'America/Mexico_City'
WHERE request_code = %s
  AND row_number = %s
  AND status = 'PENDING'
RETURNING request_code, row_number;

UPDATE {cooler_request_table}
SET
    status = 'CANCELLED',
    updated_at = CURRENT_TIMESTAMP AT TIME ZONE 'America/Mexico_City'
WHERE request_code = %s
  AND row_number = %s
  AND status = 'PENDING'
RETURNING request_code, row_number;

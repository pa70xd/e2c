UPDATE {email_request_table}
SET
    status = 'COMPLETED',
    completed_at = CURRENT_TIMESTAMP,
    updated_at = CURRENT_TIMESTAMP
WHERE request_code = %s
  AND status <> 'COMPLETED'
RETURNING request_code;
UPDATE {email_request_table}
SET
    status = 'CANCELLED',
    updated_at = CURRENT_TIMESTAMP
WHERE request_code = %s
  AND status IN ('COMPLETED', 'IN_PROGRESS')
RETURNING request_code;
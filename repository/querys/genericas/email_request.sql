INSERT INTO {email_request_table} (
    request_code,
    customer,
    status,
    priority,
    total_coolers,
    pending_coolers,
    completed_coolers,
    failed_coolers,
    assigned_to,
    started_at,
    completed_at,
    created_at,
    updated_at
) VALUES (
    %s,
    %s,
    %s,
    %s,
    %s,
    %s,
    %s,
    %s,
    %s,
    CURRENT_TIMESTAMP,
    NULL,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
)
ON CONFLICT (request_code)
DO UPDATE
SET request_code = EXCLUDED.request_code
RETURNING request_code;
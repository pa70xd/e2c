UPDATE {email_request_table} er
SET
    total_coolers = (
        SELECT COUNT(*)
        FROM {cooler_request_table} c
        WHERE c.request_code = er.request_code
          AND c.status <> 'CANCELLED'
    ),

    status = CASE
        WHEN (
            SELECT COUNT(*)
            FROM {cooler_request_table} c
            WHERE c.request_code = er.request_code
              AND c.status = 'PENDING'
        ) = 0
        THEN 'COMPLETED'
        ELSE 'IN_PROGRESS'
    END,

    completed_coolers = (
        SELECT COUNT(*)
        FROM {cooler_request_table} c
        WHERE c.request_code = er.request_code
          AND c.status = 'ACCEPTED'
    ),

    failed_coolers = (
        SELECT COUNT(*)
        FROM {cooler_request_table} c
        WHERE c.request_code = er.request_code
          AND c.status = 'CANCELLED'
    ),

    pending_coolers = (
        SELECT COUNT(*)
        FROM {cooler_request_table} c
        WHERE c.request_code = er.request_code
          AND c.status = 'PENDING'
    ),

    completed_at = CASE
        WHEN (
            SELECT COUNT(*)
            FROM {cooler_request_table} c
            WHERE c.request_code = er.request_code
              AND c.status = 'PENDING'
        ) = 0
        THEN CURRENT_TIMESTAMP
        ELSE NULL
    END,

    updated_at = CURRENT_TIMESTAMP

WHERE er.request_code = %s

RETURNING
    er.request_code,
    er.status,
    er.total_coolers,
    er.completed_coolers,
    er.failed_coolers,
    er.pending_coolers;
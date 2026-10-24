SELECT
    request_code,
    customer,
    status,
    priority,

    total_coolers,
    completed_coolers,
    failed_coolers,
    pending_coolers,

    assigned_to,

    created_at,
    updated_at,
    completed_at

FROM {email_request_table}

WHERE customer = 'danone'

ORDER BY created_at DESC;
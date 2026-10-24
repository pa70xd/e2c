SELECT
    er.request_code,
    er.status,
    er.total_coolers,
    er.completed_coolers,
    er.pending_coolers,
    er.failed_coolers,

    ARRAY_AGG(
    cr.ticket_solicitud
    ORDER BY cr.row_number
             ) FILTER (
        WHERE cr.status = 'ACCEPTED'
            AND cr.ticket_solicitud IS NOT NULL
        ) AS tickets_accepted,

    ARRAY_AGG(
    cr.ticket_solicitud
    ORDER BY cr.row_number
             ) FILTER (
        WHERE cr.status = 'PENDING'
            AND cr.ticket_solicitud IS NOT NULL
        ) AS tickets_pending,

    ARRAY_AGG(
    cr.ticket_solicitud
    ORDER BY cr.row_number
             ) FILTER (
        WHERE cr.status = 'CANCELLED'
            AND cr.ticket_solicitud IS NOT NULL
        ) AS tickets_cancelled

FROM {email_request_table} er
         LEFT JOIN {cooler_request_table} cr
                   ON cr.request_code = er.request_code

WHERE er.request_code = %s

GROUP BY
    er.request_code,
    er.status,
    er.total_coolers,
    er.completed_coolers,
    er.pending_coolers,
    er.failed_coolers;
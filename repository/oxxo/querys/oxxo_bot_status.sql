-- bot.estatus: misma salida que genericas/email_request_bot_status.sql (para
-- msj_status_solicitud), con listas por folio en lugar de TE.
SELECT
    er.request_code,
    er.status,
    er.total_coolers,
    er.completed_coolers,
    er.pending_coolers,
    er.failed_coolers,

    ARRAY_AGG(cr.folio ORDER BY cr.row_number)
        FILTER (WHERE cr.status = 'ACCEPTED' AND cr.folio IS NOT NULL)
        AS tickets_accepted,

    ARRAY_AGG(cr.folio ORDER BY cr.row_number)
        FILTER (WHERE cr.status = 'PENDING' AND cr.folio IS NOT NULL)
        AS tickets_pending,

    ARRAY_AGG(cr.folio ORDER BY cr.row_number)
        FILTER (WHERE cr.status = 'CANCELLED' AND cr.folio IS NOT NULL)
        AS tickets_cancelled

FROM {email_request_table} er
LEFT JOIN {cooler_request_table} cr
    ON cr.request_code = er.request_code
   AND cr.cliente = %s

WHERE er.request_code = %s
  AND er.customer = %s

GROUP BY
    er.request_code,
    er.status,
    er.total_coolers,
    er.completed_coolers,
    er.pending_coolers,
    er.failed_coolers;

-- bot.estatus: misma salida que genericas/email_request_bot_status.sql.
-- Lista por ORDEN (ruta) o serie (D2D, sin folio).
SELECT
    er.request_code,
    er.status,
    er.total_coolers,
    er.completed_coolers,
    er.pending_coolers,
    er.failed_coolers,

    ARRAY_AGG(COALESCE(cr.folio, cr.serie_fabricante) ORDER BY cr.row_number)
        FILTER (WHERE cr.status = 'ACCEPTED' AND COALESCE(cr.folio, cr.serie_fabricante) IS NOT NULL)
        AS tickets_accepted,

    ARRAY_AGG(COALESCE(cr.folio, cr.serie_fabricante) ORDER BY cr.row_number)
        FILTER (WHERE cr.status = 'PENDING' AND COALESCE(cr.folio, cr.serie_fabricante) IS NOT NULL)
        AS tickets_pending,

    ARRAY_AGG(COALESCE(cr.folio, cr.serie_fabricante) ORDER BY cr.row_number)
        FILTER (WHERE cr.status = 'CANCELLED' AND COALESCE(cr.folio, cr.serie_fabricante) IS NOT NULL)
        AS tickets_cancelled

FROM {email_request_table} er
LEFT JOIN {cooler_request_table} cr
    ON cr.request_code = er.request_code
   AND cr.cliente = '{cliente}'

WHERE er.request_code = %s
  AND er.customer = '{customer}'

GROUP BY
    er.request_code,
    er.status,
    er.total_coolers,
    er.completed_coolers,
    er.pending_coolers,
    er.failed_coolers;

SELECT
    row_number,
    serie_fabricante,
    serie_dnn_bnf,
    status
FROM {cooler_request_table}
WHERE request_code = %s
ORDER BY row_number;

-- request_code(s) que dieron de alta cada CASO2 (folio). Un outbound puede
-- cubrir casos de varios correos inbound.
SELECT DISTINCT request_code
FROM {cooler_request_table}
WHERE cliente = '{cliente}'
  AND folio = ANY(%s);

-- Solo lectura. Todos los registros de emails_log de las conversaciones pedidas.
SELECT
    id,
    graph_message_id,
    internet_message_id,
    conversation_id,
    request_code,
    direction,
    processing_status,
    customer,
    created_at
FROM {emails_log_table}
WHERE conversation_id = ANY(%s)
ORDER BY created_at, id

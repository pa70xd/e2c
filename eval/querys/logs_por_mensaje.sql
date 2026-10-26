-- Solo lectura. Un registro de emails_log por mensaje (por id de Graph o por Message-ID de internet).
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
WHERE graph_message_id = ANY(%s)
   OR internet_message_id = ANY(%s)

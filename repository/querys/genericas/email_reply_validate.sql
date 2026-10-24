SELECT
    id,
    request_code,
    graph_message_id,
    internet_message_id,
    conversation_id,
    conversation_index,
    parent_message_id,
    direction,
    subject,
    processing_status,
    customer,
    created_at,
    link_email
FROM {emails_log_table}
WHERE conversation_id = %s
ORDER BY
  CASE
    WHEN LOWER(
      REGEXP_REPLACE(subject, '^(re:|fw:|rv:)\s*', '', 'i')
    ) = LOWER(
      REGEXP_REPLACE(%s, '^(re:|fw:|rv:)\s*', '', 'i')
    ) THEN 0
    ELSE 1
  END,
  created_at
LIMIT 1;

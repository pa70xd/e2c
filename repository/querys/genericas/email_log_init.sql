INSERT INTO {emails_log_table} (
    graph_message_id,
    internet_message_id,
    conversation_id,
    conversation_index,
    parent_message_id,
    change_key,
    direction,
    sender_name,
    sender_email,
    recipients_to,
    recipients_cc,
    recipients_bcc,
    subject,
    body,
    has_attachments,
    attachment_count,
    processing_status,
    processing_message,
    received_at,
    sent_at,
    customer,
    link_email
)
VALUES (
    %s, %s, %s, %s,
    %s, %s, %s, %s, %s,
    %s::jsonb, %s::jsonb, %s::jsonb,
    %s, %s, %s, %s,
    %s, %s, %s, %s, %s, %s
)
ON CONFLICT (graph_message_id)
DO UPDATE
SET graph_message_id = EXCLUDED.graph_message_id
RETURNING request_code;
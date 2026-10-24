SELECT EXISTS (
    SELECT 1
    FROM {emails_log_table}
    WHERE conversation_id = %s
) AS exists_conversation;

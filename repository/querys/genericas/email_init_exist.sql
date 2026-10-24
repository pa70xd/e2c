            SELECT EXISTS (
                SELECT 1
                FROM {emails_log_table}
                WHERE graph_message_id = %s
            ) AS exists_email;
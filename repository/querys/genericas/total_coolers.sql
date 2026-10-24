            SELECT total_coolers,
            completed_coolers,
            pending_coolers,
            failed_coolers
            FROM {email_request_table}
            WHERE request_code = %s;
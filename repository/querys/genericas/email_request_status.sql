SELECT status 
FROM {email_request_table}
WHERE request_code = %s;
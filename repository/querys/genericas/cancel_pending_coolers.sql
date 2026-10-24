UPDATE {cooler_request_table} 
SET status = 'CANCELLED'
WHERE request_code = %s 
AND status = 'PENDING'
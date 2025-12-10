-- Quick SQL query to count bank rules
-- Run this directly in your database

SELECT 
    COUNT(*) as total_rules,
    COUNT(*) FILTER (WHERE is_active = true) as active_rules,
    COUNT(*) FILTER (WHERE is_active = false) as inactive_rules
FROM pharma.bank_rules;

-- Count by pharmacy
SELECT 
    pharmacy_id,
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE is_active = true) as active,
    COUNT(*) FILTER (WHERE is_active = false) as inactive
FROM pharma.bank_rules
GROUP BY pharmacy_id
ORDER BY pharmacy_id;

-- List all rules with details
SELECT 
    id,
    pharmacy_id,
    name,
    type,
    priority,
    is_active,
    created_at
FROM pharma.bank_rules
ORDER BY pharmacy_id, priority, created_at;

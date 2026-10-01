{{ config(
    materialized='table',
    schema="03_data_warehouse"
) }}

SELECT 
    c.customer_unique_id,
    MIN(o.purchased_at) AS first_order_at,
    MAX(o.purchased_at) AS last_order_at,
    COUNT(o.order_id) AS order_count
FROM {{ ref('stg_customers') }} AS c 
LEFT JOIN {{ ref('stg_orders') }} AS o 
    ON c.customer_id = o.customer_id
GROUP BY c.customer_unique_id
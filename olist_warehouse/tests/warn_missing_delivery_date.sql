{{ config(severity='warn') }}

SELECT  
    order_id,
    order_status,
    delivered_at
FROM {{ ref('fct_orders') }}
WHERE is_missing_delivery_date = TRUE
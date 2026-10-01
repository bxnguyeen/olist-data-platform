{{ config(
    materialized='table',
    schema='03_data_warehouse'
) }}

SELECT 
    o.order_id,
    o.customer_id,
    c.customer_unique_id,
    order_status,
    purchased_at,
    approved_at,
    handed_to_carrier_at,
    delivered_at,
    estimated_delivery_at,

    CASE 
        WHEN order_status = 'delivered'
            AND purchased_at IS NOT NULL 
            AND delivered_at IS NOT NULL 
        THEN EXTRACT(
            EPOCH FROM (delivered_at - purchased_at)
        ) / 86400.0
        ELSE NULL
    END AS delivery_days,

    CASE
        WHEN order_status = 'delivered'
            AND delivered_at IS NOT NULL 
            AND estimated_delivery_at IS NOT NULL 
        THEN delivered_at::date > estimated_delivery_at::date
        ELSE NULL
    END AS is_late_delivery,

    (
        order_status = 'delivered'
         AND delivered_at IS NULL 
    ) AS is_missing_delivery_date

FROM {{ ref('stg_orders')}} AS o 
LEFT JOIN {{ ref('stg_customers') }} AS c 
    ON o.customer_id = c.customer_id
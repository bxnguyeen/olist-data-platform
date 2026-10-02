{{ config(
    materialized='table',
    schema='03_data_warehouse'
) }}

SELECT 
    i.order_id,
    i.order_item_id,
    i.product_id,
    i.seller_id,
    o.purchased_at,
    o.order_status,
    i.shipping_limit_date,
    i.price,
    i.freight_value,
    (i.price + i.freight_value) AS item_total_amount
FROM {{ ref('stg_order_items') }} AS i 
LEFT JOIN {{ ref('stg_orders') }} AS o 
    ON i.order_id = o.order_id 
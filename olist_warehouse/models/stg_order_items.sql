{{ config(
    materialized='table',
    schema='02_stg'
) }}

SELECT 
    order_id,
    
    CAST(order_item_id AS INTEGER)
        AS order_item_id,
    
    product_id,
    seller_id,

    CAST(NULLIF(TRIM(shipping_limit_date), '') AS TIMESTAMP)
        AS shipping_limit_date,
    
    CAST(price AS DECIMAL(12, 2)) AS price,

    CAST(freight_value AS DECIMAL(12, 2)) AS freight_value

FROM {{ source('olist', 'order_items') }}
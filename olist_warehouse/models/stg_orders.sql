{{ config(
    materialized='table',
    schema='02_stg'
) }}

SELECT
    order_id,
    customer_id,
    order_status,

    CAST(NULLIF(TRIM(order_purchase_timestamp), '') AS TIMESTAMP)
        AS purchased_at,

    CAST(NULLIF(TRIM(order_approved_at), '') AS TIMESTAMP)    
        AS approved_at,
    
    CAST(NULLIF(TRIM(order_delivered_carrier_date), '') AS TIMESTAMP)
        AS handed_to_carrier_at,

    CAST(NULLIF(TRIM(order_delivered_customer_date), '') AS TIMESTAMP)
        AS delivered_at,

    CAST(NULLIF(TRIM(order_estimated_delivery_date), '') AS TIMESTAMP)
        AS estimated_delivery_at 

FROM {{ source('olist', 'orders') }}
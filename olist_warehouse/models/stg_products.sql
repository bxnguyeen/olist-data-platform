{{ config(
    materialized='table',
    schema='02_stg'
) }}

SELECT
    product_id,
    product_category_name,
    CAST(product_name_lenght AS INTEGER) 
        AS product_name_length,
    CAST(product_description_lenght AS INTEGER)
        AS product_description_length,
    CAST(product_photos_qty AS INTEGER)
        AS product_photos_qty,
    CAST(product_weight_g AS DECIMAL(12, 2))
        AS product_weight_g,
    CAST(product_length_cm AS DECIMAL(12, 2))
        AS product_length_cm,
    CAST(product_height_cm AS DECIMAL(12, 2))
        AS product_height_cm,
    CAST(product_width_cm AS DECIMAL(12, 2))
        AS product_width_cm
FROM {{ source('olist', 'products') }}
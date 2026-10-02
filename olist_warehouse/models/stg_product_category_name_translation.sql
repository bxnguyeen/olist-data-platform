{{ config(
    materialized='table',
    schema='02_stg'
) }}

SELECT 
    product_category_name,
    product_category_name_english
FROM {{ source('olist', 'product_category_name_translation') }}
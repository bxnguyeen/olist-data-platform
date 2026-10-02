WITH row_counts AS (
    SELECT 
        (SELECT COUNT(*)
        FROM {{ source('olist', 'order_items') }}) AS raw_count,

        (SELECT COUNT(*)
        FROM {{ ref('stg_order_items') }}) AS staging_count,

        (SELECT COUNT(*)
        FROM {{ ref('fct_order_items') }}) AS warehouse_count
)
SELECT *
FROM row_counts
WHERE raw_count <> staging_count
    OR staging_count <> warehouse_count
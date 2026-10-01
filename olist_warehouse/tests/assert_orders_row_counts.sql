WITH row_counts AS (
    SELECT 
        (SELECT COUNT(*)
        FROM {{ source('olist', 'orders') }}) AS raw_count,

        (SELECT COUNT(*)
        FROM {{ ref('stg_orders') }}) AS staging_count,

        (SELECT COUNT(*)
        FROM {{ ref('fct_orders') }}) AS warehouse_count
)
SELECT *
FROM row_counts
WHERE raw_count <> staging_count
    OR staging_count <> warehouse_count
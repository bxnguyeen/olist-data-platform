WITH row_counts AS (
    SELECT 
        (SELECT COUNT(*)
        FROM {{ source('olist', 'products') }}) AS raw_count,

        (SELECT COUNT(*)
        FROM {{ ref('stg_products') }}) AS staging_count,

        (SELECT COUNT(*)
        FROM {{ ref('dim_products') }}) AS warehouse_count
)
SELECT *
FROM row_counts
WHERE raw_count <> staging_count
    OR staging_count <> warehouse_count
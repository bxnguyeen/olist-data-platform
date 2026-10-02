SELECT *
FROM {{ ref('fct_order_items') }}
WHERE price IS NULL
    OR freight_value IS NULL
    OR price < 0
    OR freight_value < 0
    OR item_total_amount IS DISTINCT FROM (price + freight_value)
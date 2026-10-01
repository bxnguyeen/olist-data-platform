-- Run this script while connected to olist_database.
-- Create the raw schema and source-aligned tables.

CREATE SCHEMA IF NOT EXISTS "01_raw";

CREATE TABLE IF NOT EXISTS "01_raw".orders (
    order_id TEXT,
    customer_id TEXT,
    order_status TEXT,
    order_purchase_timestamp TEXT,
    order_approved_at TEXT,
    order_delivered_carrier_date TEXT,
    order_delivered_customer_date TEXT,
    order_estimated_delivery_date TEXT
);

CREATE TABLE IF NOT EXISTS "01_raw".customers (
    customer_id TEXT,
    customer_unique_id TEXT,
    customer_zip_code_prefix TEXT,
    customer_city TEXT,
    customer_state TEXT
);
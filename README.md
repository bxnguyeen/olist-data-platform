# Olist Data Pipeline — Implementation Progress Report

## 1. Objective

Build a three-layer data pipeline using dbt for data transformation:

**`01_raw` → `02_stg` → `03_data_warehouse`**

The current implementation covers orders and customers from the Olist Brazilian E-Commerce dataset.

## 2. Architecture

```text
Source CSV files
    ↓ Manual upload
MinIO object storage
    ↓ Python streaming ingestion
PostgreSQL: 01_raw
    ↓ dbt transformations
PostgreSQL: 02_stg
    ↓ dbt business models
PostgreSQL: 03_data_warehouse
```

| Component | Responsibility |
|---|---|
| MinIO | Stores the original CSV files |
| Python | Reads files from MinIO, validates their structure and loads PostgreSQL |
| PostgreSQL | Stores all three data layers and executes SQL |
| dbt Core | Manages SQL transformations, model dependencies and data tests |
| Docker Compose | Runs the project’s MinIO service |
| VS Code / DBeaver | Support development and inspection |

PostgreSQL runs separately through Postgres.app on macOS. Trino is not part of the current implementation.

## 3. Data Layers

### `01_raw` — Source-aligned data

Tables: `orders`, `customers`.

Both tables contain **99,441 rows**. Columns are stored as text to preserve source representations, including identifiers and postal-code prefixes. Original CSV files remain available in MinIO.

### `02_stg` — Standardized data

Models: `stg_orders`, `stg_customers`.

Transformations include standardizing column names, converting order timestamps, trimming surrounding whitespace, normalizing customer location text and converting empty strings to NULL where specified.

### `03_data_warehouse` — Business-oriented data

**`fct_orders`: one row per order**

Contains order details, customer identifiers, delivery duration, late-delivery status and a missing-delivery-date flag.

**`dim_customers`: one row per `customer_unique_id`**

Contains the customer identifier, first and latest order timestamps, and order count. Dates and counts cover all order statuses in the available dataset.

This initial customer model includes aggregated order attributes. Customer location is not reduced to a single latest address, because location can differ between orders.

## 4. Ingestion and Execution

The Python loader streams CSV data into PostgreSQL temporary tables without loading entire files into Python memory.

It validates column names and order, rejects empty datasets, and uses PostgreSQL COPY to parse and load CSV records. After both temporary tables are loaded, it replaces the raw data and compares raw row counts with temporary-table counts.

Both raw-table replacements occur in one transaction. An ingestion failure before commit rolls back the changes. Repeated loads replace existing data instead of appending duplicate rows.

The pipeline runs with:

```bash
python scripts/run_pipeline.py
```

The runner loads raw data first, then invokes dbt. If ingestion fails, dbt is not started.

## 5. Validation Results

Based on the completed runs:

- Raw orders and customers each contain **99,441 rows**.
- The customer dimension contains **96,096 distinct customers**.
- Customer order counts sum to **99,441 orders**.
- Configured key, relationship and row-count tests passed.
- **8 delivered orders lack an actual delivery timestamp** and generate a warning.
- A deliberate failure after raw-table truncation was tested; both raw tables retained their previous row counts after rollback.

## 6. Business Rules and Limitations

Late delivery is evaluated only for orders marked `delivered` with both actual and estimated delivery dates available. Comparison uses calendar dates, so delivery on the promised date is considered on time. Orders that cannot be evaluated retain NULL rather than being classified as on time.

The implementation currently uses full refresh ingestion. File upload to MinIO and pipeline invocation remain manual; scheduled execution is not configured.

Raw ingestion and dbt execution are not one shared transaction. If ingestion commits and dbt subsequently fails, the refreshed raw data remains.

Streaming has been verified with the current dataset, not benchmarked on files of tens of gigabytes. Temporary tables require additional PostgreSQL storage. Row-count reconciliation does not independently prove that the source files are complete or that every value is correct.

## 7. Role of dbt

dbt organizes SQL into reusable models, resolves dependencies through `source()` and `ref()`, and executes configured data tests. PostgreSQL performs the computation and stores the results.

This demonstrates dbt’s value over separately maintained manual SQL scripts: repeatable execution, explicit dependencies and automated validation. Python remains responsible for ingestion.

## 8. Current Status

A working pipeline for orders and customers has been implemented and rerun successfully, including streaming ingestion, transformation, data testing and a rollback exercise.

Potential next steps include broader data-quality coverage, reproducible dependency setup, scheduling and additional source tables.
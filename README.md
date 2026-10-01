# Olist Data Platform

A three-layer data pipeline for the Olist Brazilian E-Commerce dataset, using MinIO, Python, PostgreSQL, and dbt Core.

The current implementation processes **orders and customers**.

## Architecture

```text
Local CSV files
    │ upload_to_minio.py
    ▼
MinIO: olist-raw
    │ load_raw.py
    ▼
PostgreSQL: 01_raw
    │ dbt
    ▼
PostgreSQL: 02_stg
    │ dbt
    ▼
PostgreSQL: 03_data_warehouse
```

- **MinIO:** stores source CSV files.
- **Python:** uploads files and streams CSV data into PostgreSQL.
- **PostgreSQL:** stores the three data layers and executes SQL.
- **dbt:** manages transformations, dependencies, and data tests.
- **Docker Compose:** runs MinIO. PostgreSQL is configured separately.

## Requirements

Developed and tested on macOS with Python 3.13 and PostgreSQL 18.

Required software:

- Python with `venv`
- Docker with Docker Compose
- PostgreSQL
- Git
- A PostgreSQL client such as DBeaver or `psql`

Compatibility with other environments has not yet been verified.

## Setup

### 1. Prepare the Python environment

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### 2. Configure environment variables

Copy `.env.example` to `.env` and replace the placeholder values.

Set:

- MinIO username and password
- PostgreSQL host, port, database, username, and password
- `SOURCE_DATA_DIR`, pointing to the directory containing the source CSV files

Do not commit `.env` or real credentials.

### 3. Start MinIO

```bash
docker compose up -d minio
docker compose ps
```

Open the console at `http://localhost:9101` and sign in using the credentials in `.env`.

Create a bucket named:

```text
olist-raw
```

The upload script expects this bucket to exist. Python accesses the MinIO API at `http://localhost:9100`.

### 4. Prepare PostgreSQL

Start PostgreSQL and connect to an existing database, such as `postgres`.

Create the project database if it does not already exist:

```sql
CREATE DATABASE olist_database;
```

Connect to `olist_database` and execute:

```text
sql/00_create_raw_tables.sql
```

The configured PostgreSQL user must have permission to create schemas and tables, load data, and execute the dbt models.

### 5. Configure dbt

Copy the profile block from `profiles.example.yml` into:

```text
~/.dbt/profiles.yml
```

Replace the sample connection values. If the file already contains other profiles, preserve them and add the project profile.

The top-level profile name must match the `profile` setting in `olist_warehouse/dbt_project.yml`.

Python reads `.env`; dbt reads `profiles.yml`. Keep their PostgreSQL connection settings consistent.

Verify the connection:

```bash
cd olist_warehouse
dbt debug
cd ..
```

### 6. Obtain the source data

Download the [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), following the source’s access requirements and license terms.

Place these files in `SOURCE_DATA_DIR`:

```text
olist_orders_dataset.csv
olist_customers_dataset.csv
```

Source datasets and credentials are not included in this repository.

### 7. Upload and check the files

From the repository root, with the virtual environment active:

```bash
python scripts/upload_to_minio.py
python scripts/check_minio.py
python scripts/check_postgres.py
```

Uploading uses the same object names in MinIO and updates their contents. The two uploads are not a shared transaction.

`check_postgres.py` reports the raw orders count. A newly initialized database has zero rows until the first load.

## Run the Pipeline

Ensure MinIO and PostgreSQL are running, then execute from the repository root:

```bash
python scripts/run_pipeline.py
```

The runner:

1. Loads both CSV files from MinIO into raw tables.
2. Builds the selected dbt models and runs their tests.
3. Stops before dbt if raw ingestion fails.

Upload is a separate step. Run `upload_to_minio.py` when preparing or replacing source files.

To run the steps separately:

```bash
python scripts/load_raw.py
```

```bash
cd olist_warehouse
dbt build --select +fct_orders +dim_customers
```

## Data Models

| Layer | Model or table | Row grain |
|---|---|---|
| `01_raw` | `orders` | One source order record |
| `01_raw` | `customers` | One source customer record identified by `customer_id` |
| `02_stg` | `stg_orders` | One standardized order |
| `02_stg` | `stg_customers` | One standardized `customer_id` record |
| `03_data_warehouse` | `fct_orders` | One order |
| `03_data_warehouse` | `dim_customers` | One `customer_unique_id` |

In Olist, `customer_id` links a customer record to an order. `customer_unique_id` identifies the same customer across multiple orders.

The customer dimension includes first/latest order timestamps and order count, calculated across all order statuses. These are aggregated attributes in the initial implementation.

Customer location is not reduced to a single latest location, because it can differ between orders.

## Ingestion Behavior

The loader:

- Validates CSV column names and order.
- Streams CSV data into temporary PostgreSQL tables.
- Rejects datasets without data rows.
- Refreshes both raw tables in one transaction.
- Compares raw row counts against temporary-table counts.

Repeated execution replaces raw data rather than appending duplicate rows. Failures before commit roll back changes in the ingestion transaction.

Temporary tables require additional PostgreSQL storage. Streaming has been exercised with the current dataset, but has not been benchmarked on files of tens of gigabytes.

## Data Quality and Business Rules

Configured tests cover:

- Non-null and unique identifiers
- Relationships between orders and customers
- Fact-to-dimension customer relationships
- Order row counts across layers
- Delivered orders missing their actual delivery timestamp

Late delivery is evaluated only for orders marked `delivered` with both actual and estimated delivery timestamps available.

The comparison uses calendar dates. Delivery on the estimated date is considered on time. Orders that cannot be evaluated retain NULL.

With the current source files:

- Raw orders: **99,441**
- Raw customer records: **99,441**
- Distinct customers: **96,096**
- Delivered orders missing an actual delivery timestamp: **8**

The eight missing timestamps produce a warning rather than an error.

## Validation Performed

- Repeated ingestion preserved expected row counts.
- The selected dbt models and tests completed with the known delivery-date warning.
- A controlled failure after raw-table truncation was exercised; both raw tables retained their previous row counts after rollback.

The rollback exercise checked row counts, not a full comparison of every value.

## Current Limitations

- Source acquisition and pipeline invocation are not scheduled.
- The pipeline currently processes only orders and customers.
- Upload size checks are not content-checksum comparisons.
- Raw row counts are compared with temporary tables, not an independent source manifest.
- Raw ingestion and dbt execution do not share one transaction. If dbt fails after ingestion commits, refreshed raw data remains.
- Full refresh loading is used; incremental ingestion is not implemented.

## Data Attribution

This is an independent educational project using the Olist public dataset. It is not affiliated with or endorsed by Olist.
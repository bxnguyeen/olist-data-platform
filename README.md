# Olist Data Platform

An educational data pipeline for the Olist Brazilian E-Commerce dataset, using MinIO, Python, PostgreSQL, and dbt Core.

The current implementation processes five source tables and builds order, customer, order-item, and product models.

## Architecture

```text
Source CSV files
    │ Manual upload or upload_to_minio.py
    ▼
MinIO: olist-raw
    │ load_raw.py
    ▼
PostgreSQL: 01_raw
    │ dbt staging models
    ▼
PostgreSQL: 02_stg
    │ dbt fact and dimension models
    ▼
PostgreSQL: 03_data_warehouse
    │
    ▼
DBeaver: exploration and validation
```

- **MinIO:** stores source CSV files.
- **Python:** uploads files and streams CSV data into PostgreSQL.
- **PostgreSQL:** stores data and executes SQL.
- **dbt Core:** manages transformations, dependencies, documentation, and data tests.
- **DBeaver:** supports data exploration and manual validation.
- **Docker Compose:** runs MinIO. PostgreSQL is configured separately.

## Requirements

The project was developed on macOS with Python 3.13 and PostgreSQL 18.

Required software:

- Python with `venv`
- Docker with Docker Compose
- PostgreSQL
- Git
- A PostgreSQL client such as DBeaver or `psql`

Compatibility with other environments has not yet been verified.

## Source Data

Download the [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce).

The pipeline expects these objects at the root of the MinIO bucket `olist-raw`:

```text
olist_orders_dataset.csv
olist_customers_dataset.csv
olist_order_items_dataset.csv
olist_products_dataset.csv
product_category_name_translation.csv
```

Source datasets and credentials are not included in the repository.

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

Configure:

- MinIO username and password
- PostgreSQL host, port, database, username, and password
- `SOURCE_DATA_DIR`, the local CSV directory used by the upload script

Do not commit `.env` or real credentials.

### 3. Start MinIO

```bash
docker compose up -d minio
docker compose ps
```

- Console: `http://localhost:9101`
- API used by Python: `http://localhost:9100`

Sign in and create a bucket named `olist-raw`.

### 4. Prepare PostgreSQL

Create the project database if it does not already exist:

```sql
CREATE DATABASE olist_database;
```

Connect to that database and initialize the raw tables.

The loader requires these tables to exist in schema `01_raw`:

```text
orders
customers
order_items
products
product_category_name_translation
```

Their columns must match the source CSV headers.

The current `sql/00_create_raw_tables.sql` initializes orders and customers. The three additional tables were created separately in the local setup; their definitions still need to be added to the initialization script for a complete fresh setup.

The PostgreSQL user needs permission to create schemas and tables, load data, and execute dbt models.

### 5. Configure dbt

Add the profile from `profiles.example.yml` to:

```text
~/.dbt/profiles.yml
```

Replace the sample connection values and preserve any existing profiles.

The profile name must match the `profile` setting in `olist_warehouse/dbt_project.yml`.

Python reads `.env`; dbt reads `profiles.yml`. Both must point to the same PostgreSQL database.

Verify the connection:

```bash
cd olist_warehouse
dbt debug
```

### 6. Upload the source files

Upload the five CSV files through the MinIO Console, or use the upload script from the repository root:

```bash
python scripts/upload_to_minio.py
```

The script reads files from `SOURCE_DATA_DIR`. Its `FILES` list must include all five source files.

Uploads replace objects with the same names. Uploading is separate from loading PostgreSQL and is not a shared transaction across files.

## Run the Pipeline

With MinIO and PostgreSQL running and the virtual environment active, execute from the repository root:

```bash
python scripts/run_pipeline.py
```

Or, from `olist_warehouse`:

```bash
python ../scripts/run_pipeline.py
```

The runner:

1. Loads five CSV files from MinIO into PostgreSQL raw tables.
2. Builds the selected warehouse models and their upstream dependencies.
3. Runs the associated dbt tests.
4. Stops if ingestion or a dbt command fails.

The dbt selection is:

```bash
dbt build --select +fct_orders +dim_customers +fct_order_items +dim_products
```

To run ingestion separately, from the repository root:

```bash
python scripts/load_raw.py
```

To run dbt separately, from `olist_warehouse`:

```bash
dbt build --select +fct_orders +dim_customers +fct_order_items +dim_products
```

Source upload and pipeline execution are manually triggered.

## Data Models

| Layer | Model or table | Row grain |
|---|---|---|
| `01_raw` | `orders` | One source order |
| `01_raw` | `customers` | One source customer record identified by `customer_id` |
| `01_raw` | `order_items` | One item within an order |
| `01_raw` | `products` | One source product |
| `01_raw` | `product_category_name_translation` | One source category translation record |
| `02_stg` | `stg_orders` | One standardized order |
| `02_stg` | `stg_customers` | One standardized customer record |
| `02_stg` | `stg_order_items` | One standardized order item |
| `02_stg` | `stg_products` | One standardized product |
| `02_stg` | `stg_product_category_name_translation` | One category translation record |
| `03_data_warehouse` | `fct_orders` | One order |
| `03_data_warehouse` | `dim_customers` | One `customer_unique_id` |
| `03_data_warehouse` | `fct_order_items` | One `(order_id, order_item_id)` pair |
| `03_data_warehouse` | `dim_products` | One `product_id` |

### Customers

`customer_id` links a customer record to an order. `customer_unique_id` identifies the same customer across multiple orders.

`dim_customers` includes first/latest purchase timestamps and order count across all order statuses. Customer location is not reduced to one current address.

### Order items

`fct_order_items` contains:

- Order, item, product, and seller identifiers
- Purchase timestamp and order status
- Shipping deadline
- Item price and freight value
- `item_total_amount`, calculated as `price + freight_value`

`order_item_id` is an item sequence within an order, not a quantity field.

Financial totals require an explicit order-status filter where appropriate. Summing all item prices does not establish realized revenue.

### Products

`dim_products` contains product categories, English category translations, name and description lengths, photo count, weight, and dimensions.

The source misspellings `product_name_lenght` and `product_description_lenght` are preserved in raw and renamed to `product_name_length` and `product_description_length` in staging.

A `LEFT JOIN` to category translations preserves products without a matching translation. Both the original category and English category are retained.

## Ingestion Behavior

The loader:

- Validates CSV column names and order.
- Streams CSV data into temporary PostgreSQL tables.
- Rejects files without data rows.
- Loads all five files before replacing raw data.
- Refreshes the raw tables in one transaction.
- Compares loaded raw row counts against temporary-table counts.

Repeated execution replaces raw data rather than appending duplicate rows. Errors before commit roll back the ingestion transaction.

Raw ingestion and dbt execution do not share a transaction. If dbt fails after ingestion commits, the refreshed raw data remains.

## Data Quality

Tests cover:

- Required and unique identifiers
- Order/customer and item/order/product relationships
- The composite order-item key
- Row-count preservation across selected layers
- Order-item amount validation
- Delivered orders missing delivery dates
- Product categories without translations

Model metadata and generic tests are grouped in:

```text
models/stg.yml
models/fct.yml
models/dim.yml
```

Custom SQL tests are stored in `tests/`.

### Known warnings

**Missing delivery dates**

Eight orders marked as delivered lack an actual delivery timestamp. They are retained and flagged.

Late delivery is evaluated only when the order is delivered and both actual and estimated delivery timestamps are available. The comparison uses calendar dates; delivery on the estimated date is on time. Cases that cannot be evaluated retain `NULL`.

**Missing category translations**

Thirteen products belong to two categories without a matching translation:

| Category | Products |
|---|---:|
| `portateis_cozinha_e_preparadores_de_alimentos` | 10 |
| `pc_gamer` | 3 |

These products retain their original category; the English category is `NULL`.

Both exceptions produce warnings rather than stopping the pipeline.

## Validation

The latest local pipeline run reported:

```text
PASS=47 WARN=2 ERROR=0 SKIP=0 NO-OP=0 TOTAL=49
Pipeline completed.
```

The totals include model builds and tests. The two warnings correspond to the documented delivery-date and category-translation exceptions.

### Reproducibility Check

The expanded five-table pipeline was tested from a separate Git clone with a new Python virtual environment installed from `requirements.txt`.

All five raw tables were initialized using the repository SQL in a separate PostgreSQL database, `olist_repro_test_v2`. Python and dbt were configured to use this database, and the resulting warehouse tables were checked in DBeaver.

The pipeline completed with **47 PASS, 2 WARN, and 0 ERROR**. The warnings correspond to the documented missing delivery dates and category translations.

This check reused the existing PostgreSQL server and MinIO service on the same machine. It verifies rebuilding from a fresh clone and database, but does not establish a complete setup on a new machine.

### Earlier validation scope

The earlier orders/customers implementation was also exercised through repeated ingestion, a controlled rollback check, and a separate Git clone with a new virtual environment and a separate PostgreSQL database on the same machine.

Those checks reused the existing PostgreSQL server and MinIO service. They do not establish a fresh-machine setup or validate rollback and reproducibility for the expanded five-table version.

## Current Limitations

- Source acquisition, upload, and pipeline execution are not scheduled.
- Full refresh loading is used; incremental ingestion is not implemented.
- Upload size checks do not verify content checksums.
- Raw row counts are compared with temporary tables, not an independent source manifest.
- Raw loading and dbt transformations are separate transactions.
- Large-file performance has not been benchmarked.

## Data Attribution

This is an independent educational project using the Olist public dataset. It is not affiliated with or endorsed by Olist.
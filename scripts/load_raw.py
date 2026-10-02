import csv
import io
import os 
from pathlib import Path 

import boto3
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parent.parent
BUCKET = "olist-raw"
COPY_BUFFER_SIZE = 64 * 1024

TABLES = {
    "orders": [
        "order_id",
        "customer_id",
        "order_status",
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ],
    "customers": [
        "customer_id",
        "customer_unique_id",
        "customer_zip_code_prefix",
        "customer_city",
        "customer_state",
    ],
    "order_items": [
        "order_id",
        "order_item_id",
        "product_id",
        "seller_id",
        "shipping_limit_date",
        "price",
        "freight_value",
    ],
    "products": [
        "product_id",
        "product_category_name",
        "product_name_lenght",
        "product_description_lenght",
        "product_photos_qty",
        "product_weight_g",
        "product_length_cm",
        "product_height_cm",
        "product_width_cm",
    ],
    "product_category_name_translation": [
        "product_category_name",
        "product_category_name_english",
    ],
}


def load_staging_table(s3, connection, cursor, table, columns):
    if table == "product_category_name_translation":
        filename = "product_category_name_translation.csv"
    else:
        filename = f"olist_{table}_dataset.csv"
    temporary_table = sql.Identifier(f"load_{table}")
    raw_table = sql.Identifier("01_raw", table)

    column_list = sql.SQL(", ").join(
        sql.Identifier(column) for column in columns
    )

    cursor.execute(
        sql.SQL(
            "CREATE TEMP TABLE {} (LIKE {}) ON COMMIT DROP"
        ).format(temporary_table, raw_table)
    )

    response = s3.get_object(Bucket=BUCKET, Key=filename)
    body = response["Body"]

    try:
        with io.TextIOWrapper(
            body, encoding="utf-8-sig",
            newline="",
        ) as stream:
            # Read and validate only the header.
            header = next(csv.reader(stream, strict=True), None)

            if header != columns:
                raise ValueError(
                    f"{filename}: unexpected column names or order"
                )

            # The header has already been consumed.
            # PostgreSQL parses the remaining CSV data.
            copy_command = sql.SQL(
                "COPY {} ({}) FROM STDIN WITH (FORMAT CSV)"
            ).format(temporary_table, column_list)

            cursor.copy_expert(
                copy_command.as_string(connection),
                stream,
                size=COPY_BUFFER_SIZE,
            )
    finally:
        body.close()

    cursor.execute(
        sql.SQL("SELECT COUNT(*) FROM {}").format(temporary_table)
    )
    row_count = cursor.fetchone()[0]

    if row_count == 0:
        raise ValueError(f"{filename}: no data rows found")

    print(
        f"Staged {filename}: {row_count:,} rows",
        flush=True,
    )

    return row_count


def main():
    load_dotenv(PROJECT_DIR / ".env")

    s3 = boto3.client(
        "s3",
        endpoint_url="http://localhost:9100",
        aws_access_key_id=os.environ["MINIO_ROOT_USER"],
        aws_secret_access_key=os.environ["MINIO_ROOT_PASSWORD"],
        region_name="us-east-1",
    )

    connection = psycopg2.connect(
        host=os.environ["PGHOST"],
        port=os.environ["PGPORT"],
        dbname=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"],
        password=os.environ.get("PGPASSWORD", ""),
        connect_timeout=10,
    )

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute("SET LOCAL lock_timeout = '10s'")

                staged_counts = {}

                # Load both files before modifying the raw tables.
                for table, columns in TABLES.items():
                    staged_counts[table] = load_staging_table(
                        s3, connection, cursor, table, columns
                    )

                raw_tables = sql.SQL(", ").join(
                    sql.Identifier("01_raw", table)
                    for table in TABLES
                )

                cursor.execute(
                    sql.SQL("TRUNCATE TABLE {}").format(raw_tables)
                )

                for table, columns in TABLES.items():
                    raw_table = sql.Identifier("01_raw", table)
                    temporary_table = sql.Identifier(f"load_{table}")
                    column_list = sql.SQL(", ").join(
                        sql.Identifier(column) for column in columns
                    )

                    cursor.execute(
                        sql.SQL(
                            "INSERT INTO {} ({}) SELECT {} FROM {}"
                        ).format(
                            raw_table,
                            column_list,
                            column_list,
                            temporary_table,
                        )
                    )

                    cursor.execute(
                        sql.SQL("SELECT COUNT(*) FROM {}").format(raw_table)
                    )
                    raw_count = cursor.fetchone()[0]

                    if raw_count != staged_counts[table]:
                        raise ValueError(
                            f"{table}: staged {staged_counts[table]} rows, "
                            f"but raw contains {raw_count} rows"
                        )

                    print(
                        f"Verified raw {table}: {raw_count:,} rows",
                        flush=True,
                    )

        print("COMMIT successful: both raw tables refreshed.", flush=True)

    finally:
        connection.close()


if __name__ == "__main__":
    main()
import csv
import io 
import os
from pathlib import Path 

import boto3 
from dotenv import load_dotenv

# Read .env from original folder
project_dir = Path(__file__).resolve().parent.parent
load_dotenv(project_dir / ".env")

# Connect to MinIO via API gate 9100
s3 = boto3.client(
    "s3",
    endpoint_url="http://localhost:9100",
    aws_access_key_id=os.environ["MINIO_ROOT_USER"],
    aws_secret_access_key=os.environ["MINIO_ROOT_PASSWORD"],
    region_name="us-east-1",
)

files = [
    "olist_orders_dataset.csv",
    "olist_customers_dataset.csv",
]

for filename in files:
    response = s3.get_object(
        Bucket="olist-raw",
        Key=filename,
    )

    with io.TextIOWrapper(
        response["Body"], encoding="utf-8-sig", newline=""
    ) as stream:
        reader = csv.reader(stream)
        columns = next(reader)
        row_count = sum(1 for _ in reader)

    print(f"\nFile: {filename}")
    print(f"Columns: {columns}")
    print(f"Row Count: {row_count:,}")
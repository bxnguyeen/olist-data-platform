import os
from pathlib import Path

import boto3
from dotenv import load_dotenv


PROJECT_DIR = Path(__file__).resolve().parent.parent
BUCKET = "olist-raw"

FILES = [
    "olist_orders_dataset.csv",
    "olist_customers_dataset.csv",
]


def main():
    load_dotenv(PROJECT_DIR / ".env")

    source_dir = Path(os.environ["SOURCE_DATA_DIR"]).expanduser()

    # Validate both local files before uploading.
    for filename in FILES:
        file_path = source_dir / filename

        if not file_path.is_file():
            raise FileNotFoundError(f"Source file not found: {file_path}")

        if file_path.stat().st_size == 0:
            raise ValueError(f"Source file is empty: {file_path}")

    s3 = boto3.client(
        "s3",
        endpoint_url="http://localhost:9100",
        aws_access_key_id=os.environ["MINIO_ROOT_USER"],
        aws_secret_access_key=os.environ["MINIO_ROOT_PASSWORD"],
        region_name="us-east-1",
    )

    # Verify that the existing bucket is accessible.
    s3.head_bucket(Bucket=BUCKET)

    for filename in FILES:
        file_path = source_dir / filename
        local_size = file_path.stat().st_size

        print(f"Uploading {filename}...", flush=True)

        s3.upload_file(
            Filename=str(file_path),
            Bucket=BUCKET,
            Key=filename,
            ExtraArgs={"ContentType": "text/csv"},
        )

        metadata = s3.head_object(
            Bucket=BUCKET,
            Key=filename,
        )
        remote_size = metadata["ContentLength"]

        if remote_size != local_size:
            raise ValueError(
                f"{filename}: size mismatch "
                f"(local={local_size}, remote={remote_size})"
            )

        print(
            f"Uploaded and size-checked: {filename} "
            f"({remote_size:,} bytes)",
            flush=True,
        )

    print("Both files uploaded successfully.", flush=True)


if __name__ == "__main__":
    main()
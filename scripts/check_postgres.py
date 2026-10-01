import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

project_dir = Path(__file__).resolve().parent.parent
load_dotenv(project_dir / ".env")

connection = psycopg2.connect(
    host=os.environ["PGHOST"],
    port=os.environ["PGPORT"],
    dbname=os.environ["PGDATABASE"],
    user=os.environ["PGUSER"],
    password=os.environ.get("PGPASSWORD", ""),
    connect_timeout=10,
)

try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_database(), current_user")
        database, user = cursor.fetchone()

        print(f"Database: {database}")
        print(f"User: {user}")

        cursor.execute('SELECT COUNT(*) FROM "01_raw".orders')
        print(f"Raw orders: {cursor.fetchone()[0]:,}")
finally:
    connection.close()
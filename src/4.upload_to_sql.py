"""
7.upload_to_sql.py
==================
Uploads the transformed Pakistan PM2.5 CSV data into MySQL Database.

Features:
  1. Auto-detects the latest pakistan_* folder in raw_data/
  2. Reads database credentials safely from .env file
  3. Handles special characters in password (URL-encoding) to avoid connection errors
  4. Uploads 139,000+ rows in high-speed batches (chunks of 5,000 rows)
  5. Verifies upload with COUNT(*) and displays top 5 rows from MySQL

How to run:
  python src/7.upload_to_sql.py
"""

import os
import sys
import urllib.parse
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


# Windows terminal par UTF-8 encoding
sys.stdout.reconfigure(encoding="utf-8")


# --------------------------------------------------
# Step 1: Paths & Load .env
# --------------------------------------------------
SRC_FOLDER = Path(__file__).resolve().parent
PROJECT_FOLDER = SRC_FOLDER.parent
RAW_DATA_FOLDER = PROJECT_FOLDER / "raw_data"
ENV_FILE = PROJECT_FOLDER / ".env"

# Load credentials from .env
load_dotenv(ENV_FILE)

DB_PASSWORD = os.getenv("Db_Password")

if not DB_PASSWORD:
    raise ValueError("Db_Password .env file mein nahi mila! Check karein ke .env file root folder mein maujood hai.")


def find_latest_pakistan_folder():
    """Auto-detects the newest pakistan_* folder."""
    folders = [
        p for p in RAW_DATA_FOLDER.glob("pakistan_*")
        if p.is_dir() and (p / "openaq_pk_locations.json").exists()
    ]
    if not folders:
        raise FileNotFoundError("No Pakistan folder found in raw_data/")
    return max(folders, key=lambda p: p.name)


def main():
    print("=" * 60, flush=True)
    print("  UPLOAD PAKISTAN AIR QUALITY DATA TO MySQL", flush=True)
    print("=" * 60, flush=True)

    # --------------------------------------------------
    # Step 2: Read Transformed CSV
    # --------------------------------------------------
    collection_folder = find_latest_pakistan_folder()
    csv_file = collection_folder / "pakistan_pm25_transformed.csv"

    if not csv_file.exists():
        print(f"\n❌ ERROR: CSV file nahi mili: {csv_file.name}", flush=True)
        print("Pehle '5.transform_pakistan_data.py' run karein!", flush=True)
        return

    print(f"\n[1/4] Reading CSV: {csv_file.name}...", flush=True)
    df = pd.read_csv(csv_file, low_memory=False)
    print(f"  Loaded {len(df):,} rows and {len(df.columns)} columns.", flush=True)

    # --------------------------------------------------
    # Step 3: MySQL Connection Settings
    # --------------------------------------------------
    print("\n[2/4] Connecting to MySQL Database...", flush=True)

    username = "root"
    host = "localhost"
    port = "3306"
    database = "airpulseai"
    table_name = "pakistan_pm25_hourly"

    # Password mein agar '@' waghera ho to usay safely URL-encode karna
    clean_pw = urllib.parse.unquote(DB_PASSWORD)
    encoded_pw = urllib.parse.quote_plus(clean_pw)

    # Connection String (mysql-connector engine)
    connection_string = (
        f"mysql+mysqlconnector://{username}:{encoded_pw}@{host}:{port}/{database}"
    )

    try:
        engine = create_engine(connection_string)

        # Connection check query
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print(f"  Connected to database '{database}' successfully! ✅", flush=True)

    except Exception as error:
        print(f"\n❌ MySQL Connection Failed!", flush=True)
        print(f"Error Details: {error}", flush=True)
        print("\nTroubleshooting Steps:")
        print("1. Check karein ke MySQL service chal rahi hai (Windows Services mein 'MySQL' check karein).")
        print("2. Check karein ke MySQL mein database 'airpulseai' bana hua hai:")
        print("   Command: CREATE DATABASE IF NOT EXISTS airpulseai;")
        print("3. Check karein ke .env file mein password sahi hai.")
        return

    # --------------------------------------------------
    # Step 4: Batch Upload to MySQL
    # --------------------------------------------------
    print(f"\n[3/4] Uploading {len(df):,} rows to table '{table_name}'...", flush=True)
    print("  (5,000 rows ke batches mein upload ho raha hai, 30-60 seconds lagenge)...", flush=True)

    try:
        df.to_sql(
            name=table_name,
            con=engine,
            if_exists="replace",       # Table exist karti ho to naye data se replace karega
            index=False,               # Pandas index column upload na karein
            chunksize=5000             # Fast batch size
        )
        print("  Upload complete! ✅", flush=True)

    except Exception as error:
        print(f"\n❌ Error during upload: {error}", flush=True)
        return

    # --------------------------------------------------
    # Step 5: Verification Query
    # --------------------------------------------------
    print("\n[4/4] Verifying data directly from MySQL...", flush=True)

    try:
        with engine.connect() as conn:
            # Total Rows
            res_total = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).fetchone()[0]
            # Valid PM2.5 Rows
            res_pm25 = conn.execute(text(f"SELECT COUNT(pm25_value) FROM {table_name} WHERE pm25_value IS NOT NULL")).fetchone()[0]

            print(f"  Total Rows in MySQL: {res_total:,}", flush=True)
            print(f"  Valid PM2.5 Readings: {res_pm25:,}", flush=True)

            # Sample Preview
            sample_query = text(f"""
                SELECT sensor_id, location_name, pm25_value, datetime_from_utc, locality
                FROM {table_name}
                LIMIT 5
            """)
            rows = conn.execute(sample_query).fetchall()

            print("\n  Sample Preview from MySQL Table:")
            print(f"  {'Sensor ID':<12} {'Location':<25} {'PM2.5':<8} {'Date Time (UTC)':<22} {'City'}")
            print(f"  {'-'*12} {'-'*25} {'-'*8} {'-'*22} {'-'*15}")
            for r in rows:
                loc = str(r[1])[:23] if r[1] else "N/A"
                print(f"  {str(r[0]):<12} {loc:<25} {str(r[2]):<8} {str(r[3])[:19]:<22} {str(r[4])}")

    except Exception as error:
        print(f"  Verification query failed: {error}", flush=True)

    print("\n" + "=" * 60, flush=True)
    print("  SQL PIPELINE FINISHED SUCCESSFULLY! 🎉", flush=True)
    print("=" * 60, flush=True)
    print(f"Database: {database}")
    print(f"Table: {table_name}")
    print(f"Rows Uploaded: {len(df):,}")


if __name__ == "__main__":
    main()
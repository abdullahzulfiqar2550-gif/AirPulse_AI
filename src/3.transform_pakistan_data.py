"""
transform_pakistan_data.py
===========================
This script transforms Pakistan PM2.5 JSON data into a clean CSV file.

What it does (step by step):
  1. Finds the latest Pakistan data folder automatically
  2. Reads all 20 sensor hourly JSON files
  3. Flattens nested JSON into clean flat rows
  4. Adds location info (latitude, longitude, city)
  5. Adds time features for ML (hour, month, day_of_week)
  6. Saves as a clean CSV file

How to run:
  cd src
  python transform_pakistan_data.py
"""

import json
import sys
import pandas as pd
from pathlib import Path


# Fix encoding for Windows terminal
sys.stdout.reconfigure(encoding="utf-8")


# --------------------------------------------------
# Step 1: Set up folder paths
# --------------------------------------------------
SRC_FOLDER = Path(__file__).resolve().parent         # src/
PROJECT_FOLDER = SRC_FOLDER.parent                   # AirPulse_AI/
RAW_DATA_FOLDER = PROJECT_FOLDER / "raw_data"        # raw_data/


def find_latest_pakistan_folder():
    """Find the newest pakistan_* folder in raw_data/."""
    folders = []

    for path in RAW_DATA_FOLDER.glob("pakistan_*"):
        if path.is_dir() and (path / "openaq_pk_locations.json").exists():
            folders.append(path)

    if not folders:
        raise FileNotFoundError("No Pakistan collection folder found in raw_data/")

    latest_folder = max(folders, key=lambda p: p.name)
    return latest_folder


# --------------------------------------------------
# Step 2: Build a location lookup table
# --------------------------------------------------
def build_location_lookup(location_file):
    """
    Read the locations JSON and create a dictionary:
      location_id -> {name, locality, timezone, latitude, longitude, ...}

    This lets us add location info to each hourly record.
    """
    print("\nStep 2: Building location lookup table...", flush=True)

    with open(location_file, "r", encoding="utf-8") as file:
        data = json.load(file)

    lookup = {}

    for page in data.get("original_api_pages", []):
        for location in page.get("results", []):
            location_id = location.get("id")
            country = location.get("country", {})
            coordinates = location.get("coordinates", {})

            lookup[location_id] = {
                "locality": location.get("locality"),
                "timezone": location.get("timezone"),
                "country_code": country.get("code"),
                "country_name": country.get("name"),
                "latitude": coordinates.get("latitude"),
                "longitude": coordinates.get("longitude"),
            }

    print(f"  Locations in lookup: {len(lookup)}", flush=True)
    return lookup


# --------------------------------------------------
# Step 3: Read and flatten all sensor hourly files
# --------------------------------------------------
def flatten_hourly_files(hourly_folder, location_lookup):
    """
    Read each sensor JSON file and flatten every hourly record
    into a clean dictionary row for pandas.
    """
    print("\nStep 3: Reading and flattening hourly sensor files...", flush=True)

    hourly_files = sorted(hourly_folder.glob("sensor_*.json"))

    if not hourly_files:
        raise FileNotFoundError(f"No sensor files found in {hourly_folder}")

    print(f"  Sensor files found: {len(hourly_files)}", flush=True)

    # This list will hold all the clean rows
    all_rows = []

    for i, json_file in enumerate(hourly_files):

        # Read the sensor file
        with open(json_file, "r", encoding="utf-8") as file:
            data = json.load(file)

        # Get sensor-level info (same for all records in this file)
        sensor_id = data.get("sensor_id")
        location_id = data.get("location_id")
        location_name = data.get("location_name")
        is_monitor = data.get("is_monitor")
        provider_name = data.get("provider_name")

        # Get location info from our lookup
        loc_info = location_lookup.get(location_id, {})

        file_rows = 0

        # Process each API page
        for page in data.get("original_api_pages", []):
            for record in page.get("results", []):

                # Get nested fields safely
                parameter = record.get("parameter", {})
                period = record.get("period", {})
                datetime_from = period.get("datetimeFrom", {})
                datetime_to = period.get("datetimeTo", {})
                summary = record.get("summary", {})
                coverage = record.get("coverage", {})
                flag_info = record.get("flagInfo", {})

                # Create one clean flat row
                row = {
                    # Sensor info
                    "sensor_id": sensor_id,
                    "location_id": location_id,
                    "location_name": location_name,
                    "is_monitor": is_monitor,
                    "provider_name": provider_name,

                    # TARGET VARIABLE - PM2.5 value
                    "pm25_value": record.get("value"),

                    # Time info
                    "datetime_from_utc": datetime_from.get("utc"),
                    "datetime_to_utc": datetime_to.get("utc"),
                    "datetime_from_local": datetime_from.get("local"),
                    "datetime_to_local": datetime_to.get("local"),

                    # Parameter info
                    "parameter_id": parameter.get("id"),
                    "parameter_name": parameter.get("name"),
                    "units": parameter.get("units"),

                    # Summary stats
                    "summary_min": summary.get("min"),
                    "summary_max": summary.get("max"),
                    "summary_avg": summary.get("avg"),
                    "summary_median": summary.get("median"),
                    "summary_sd": summary.get("sd"),

                    # Coverage info
                    "coverage_percent": coverage.get("percentComplete"),
                    "observed_count": coverage.get("observedCount"),
                    "expected_count": coverage.get("expectedCount"),

                    # Flags
                    "has_flags": flag_info.get("hasFlags") if flag_info else None,

                    # Location info (from lookup)
                    "latitude": loc_info.get("latitude"),
                    "longitude": loc_info.get("longitude"),
                    "locality": loc_info.get("locality"),
                    "timezone": loc_info.get("timezone"),
                    "country_code": loc_info.get("country_code"),
                    "country_name": loc_info.get("country_name"),
                }

                all_rows.append(row)
                file_rows = file_rows + 1

        print(
            f"  [{i + 1}/{len(hourly_files)}] "
            f"{json_file.name} ({location_name}): {file_rows} records",
            flush=True
        )

    print(f"\n  Total rows flattened: {len(all_rows)}", flush=True)
    return all_rows


# --------------------------------------------------
# Step 4: Create DataFrame and add time features
# --------------------------------------------------
def create_dataframe(all_rows):
    """Convert the list of rows into a pandas DataFrame and add time features."""
    print("\nStep 4: Creating DataFrame and adding time features...", flush=True)

    # Create DataFrame from the flat rows
    df = pd.DataFrame(all_rows)

    # Convert datetime columns to proper datetime type
    df["datetime_from_utc"] = pd.to_datetime(df["datetime_from_utc"])
    df["datetime_to_utc"] = pd.to_datetime(df["datetime_to_utc"])
    df["datetime_from_local"] = pd.to_datetime(df["datetime_from_local"], utc=True)
    df["datetime_to_local"] = pd.to_datetime(df["datetime_to_local"], utc=True)

    # Add time features for ML models
    df["hour"] = df["datetime_from_utc"].dt.hour
    df["day_of_week"] = df["datetime_from_utc"].dt.dayofweek
    df["month"] = df["datetime_from_utc"].dt.month
    df["year"] = df["datetime_from_utc"].dt.year
    df["day_of_year"] = df["datetime_from_utc"].dt.dayofyear

    print(f"  DataFrame shape: {df.shape[0]} rows x {df.shape[1]} columns", flush=True)

    return df


# --------------------------------------------------
# Step 5: Run the full transformation
# --------------------------------------------------
def main():
    """Run the complete data transformation pipeline."""

    # Find the latest Pakistan data folder
    collection_folder = find_latest_pakistan_folder()
    location_file = collection_folder / "openaq_pk_locations.json"
    hourly_folder = collection_folder / "hourly"
    output_file = collection_folder / "pakistan_pm25_transformed.csv"

    print("========================================", flush=True)
    print("  PAKISTAN DATA TRANSFORMATION", flush=True)
    print("========================================", flush=True)
    print(f"Step 1: Data folder: {collection_folder.name}", flush=True)

    # Build location lookup
    location_lookup = build_location_lookup(location_file)

    # Flatten all hourly files
    all_rows = flatten_hourly_files(hourly_folder, location_lookup)

    # Create DataFrame with time features
    df = create_dataframe(all_rows)

    # Save to CSV
    print(f"\nStep 5: Saving CSV to {output_file.name}...", flush=True)
    df.to_csv(output_file, index=False)

    # Print final summary
    print(flush=True)
    print("========================================", flush=True)
    print("  TRANSFORMATION COMPLETE", flush=True)
    print("========================================", flush=True)
    print(f"Total records: {len(df)}", flush=True)
    print(f"Total columns: {len(df.columns)}", flush=True)
    print(f"File saved: {output_file}", flush=True)

    print(f"\nColumns:", flush=True)
    for col in df.columns:
        non_null = df[col].notna().sum()
        print(f"  {col}: {df[col].dtype} ({non_null} non-null)", flush=True)

    print(f"\nTarget variable (pm25_value):", flush=True)
    print(f"  Non-null values: {df['pm25_value'].notna().sum()}", flush=True)
    print(f"  Null values: {df['pm25_value'].isna().sum()}", flush=True)
    print(f"  Min: {df['pm25_value'].min()}", flush=True)
    print(f"  Max: {df['pm25_value'].max()}", flush=True)
    print(f"  Mean: {df['pm25_value'].mean():.2f}", flush=True)

    print(f"\nFirst 3 rows:", flush=True)
    print(df.head(3).to_string(), flush=True)


if __name__ == "__main__":
    main()



import json
import sys
from pathlib import Path

from pydantic import ValidationError

# Import our Pydantic models from entity.py
from entity import HourlyRecord, LocationRecord, OpenAQMeta


# Force UTF-8 encoding for Windows terminal
sys.stdout.reconfigure(encoding="utf-8")


# --------------------------------------------------
# Step 1: Set up folder paths
# --------------------------------------------------
SRC_FOLDER = Path(__file__).resolve().parent         # src/
PROJECT_FOLDER = SRC_FOLDER.parent                   # AirPulse_AI/
RAW_DATA_FOLDER = PROJECT_FOLDER / "raw_data"        # raw_data/


def save_json(path, data, pretty=True):
    """Save data to a JSON file safely."""
    with open(path, "w", encoding="utf-8") as file:
        if pretty:
            json.dump(data, file, indent=2, ensure_ascii=False)
        else:
            json.dump(data, file, ensure_ascii=False)


# --------------------------------------------------
# Step 2: Find the latest Pakistan collection folder
# --------------------------------------------------
def find_latest_pakistan_folder():
    """
    Looks for folders named 'pakistan_*' in raw_data/.
    Automatically selects the newest one by timestamp.
    """
    folders = []

    for path in RAW_DATA_FOLDER.glob("pakistan_*"):
        if path.is_dir() and (path / "openaq_pk_locations.json").exists():
            folders.append(path)

    if not folders:
        raise FileNotFoundError("No Pakistan collection folder found in raw_data/")

    latest_folder = max(folders, key=lambda p: p.name)
    return latest_folder


# --------------------------------------------------
# Step 3: Validate location records
# --------------------------------------------------
def validate_locations(location_file, output_folder):
    """Validate location metadata using LocationRecord model."""
    print("\n--- Validating Location Records ---", flush=True)

    with open(location_file, "r", encoding="utf-8") as file:
        data = json.load(file)

    valid_records = []
    invalid_records = []
    total_records = 0

    pages = data.get("original_api_pages", [])
    print(f"  Location API pages to check: {len(pages)}", flush=True)

    for page in pages:
        # Validate page meta
        try:
            OpenAQMeta(**page["meta"])
        except (ValidationError, KeyError, TypeError) as error:
            print(f"  Warning: Page meta invalid: {error}", flush=True)

        # Validate each location record
        for record in page.get("results", []):
            total_records += 1
            try:
                valid_record = LocationRecord(**record)
                valid_records.append(valid_record.model_dump())
            except ValidationError as error:
                invalid_records.append({
                    "record_id": record.get("id", "unknown"),
                    "error": str(error)
                })

    save_json(output_folder / "valid_locations.json", valid_records, pretty=False)
    save_json(output_folder / "invalid_locations.json", invalid_records)

    print(f"  Total location records: {total_records}", flush=True)
    print(f"  Valid locations: {len(valid_records)}", flush=True)
    print(f"  Invalid locations: {len(invalid_records)}", flush=True)

    return total_records, len(valid_records), len(invalid_records)


# --------------------------------------------------
# Step 4: Validate hourly PM2.5 records
# --------------------------------------------------
def validate_hourly_files(hourly_folder, output_folder):
    """
    Validate every hourly sensor file against HourlyRecord schema.
    Also checks:
      1. Parameter name is 'pm25' (our target variable)
      2. PM2.5 value is numeric or counts missing nulls
    """
    print("\n--- Validating Hourly PM2.5 Records ---", flush=True)

    hourly_files = sorted(hourly_folder.glob("sensor_*.json"))

    if not hourly_files:
        raise FileNotFoundError(f"No sensor files found in {hourly_folder}")

    print(f"  Sensor files found: {len(hourly_files)}", flush=True)

    valid_records = []
    invalid_records = []
    missing_value_count = 0
    total_records = 0
    files_checked = 0

    for json_file in hourly_files:
        files_checked += 1

        with open(json_file, "r", encoding="utf-8") as file:
            data = json.load(file)

        sensor_id = data.get("sensor_id")
        location_name = data.get("location_name", "Unknown")
        file_record_count = 0

        for page in data.get("original_api_pages", []):
            try:
                OpenAQMeta(**page["meta"])
            except (ValidationError, KeyError, TypeError):
                pass

            for record in page.get("results", []):
                total_records += 1
                file_record_count += 1

                try:
                    # Validate against HourlyRecord
                    valid_record = HourlyRecord(**record)

                    # Check 1: Target variable parameter must be pm25
                    if valid_record.parameter.name != "pm25":
                        raise ValueError(f"Expected pm25, got {valid_record.parameter.name}")

                    row = valid_record.model_dump()
                    row["sensor_id"] = sensor_id
                    valid_records.append(row)

                    # Check 2: Is PM2.5 value present?
                    if valid_record.value is None:
                        missing_value_count += 1

                except (ValidationError, ValueError) as error:
                    invalid_records.append({
                        "sensor_id": sensor_id,
                        "file": json_file.name,
                        "error": str(error)[:200]
                    })

        print(
            f"  [{files_checked}/{len(hourly_files)}] "
            f"{json_file.name} ({location_name}): {file_record_count} records",
            flush=True
        )

    # Save validation outputs
    save_json(output_folder / "valid_hourly.json", valid_records, pretty=False)
    save_json(output_folder / "invalid_hourly.json", invalid_records)

    print(f"\n  Hourly files checked: {files_checked}", flush=True)
    print(f"  Total hourly records: {total_records}", flush=True)
    print(f"  Valid records: {len(valid_records)}", flush=True)
    print(f"  Invalid records: {len(invalid_records)}", flush=True)
    print(f"  Records with missing PM2.5 value: {missing_value_count}", flush=True)

    return {
        "hourly_files_checked": files_checked,
        "hourly_records_checked": total_records,
        "valid_hourly_records": len(valid_records),
        "invalid_hourly_records": len(invalid_records),
        "missing_pm25_values": missing_value_count
    }


# --------------------------------------------------
# Step 5: Main execution
# --------------------------------------------------
def main():
    collection_folder = find_latest_pakistan_folder()
    location_file = collection_folder / "openaq_pk_locations.json"
    hourly_folder = collection_folder / "hourly"

    # Create validation subfolder inside the latest collection folder
    output_folder = collection_folder / "validation"
    output_folder.mkdir(exist_ok=True)

    print("========================================", flush=True)
    print("  PAKISTAN DATA VALIDATION", flush=True)
    print("========================================", flush=True)
    print(f"Target folder: {collection_folder.name}", flush=True)

    # Run validations
    loc_total, loc_valid, loc_invalid = validate_locations(location_file, output_folder)
    hourly_summary = validate_hourly_files(hourly_folder, output_folder)

    # Save summary report
    summary = {
        "collection_folder": str(collection_folder),
        "location_records_checked": loc_total,
        "valid_locations": loc_valid,
        "invalid_locations": loc_invalid,
        **hourly_summary,
        "output_files": {
            "valid_locations": str(output_folder / "valid_locations.json"),
            "invalid_locations": str(output_folder / "invalid_locations.json"),
            "valid_hourly": str(output_folder / "valid_hourly.json"),
            "invalid_hourly": str(output_folder / "invalid_hourly.json"),
        }
    }
    save_json(output_folder / "validation_summary.json", summary)

    print(flush=True)
    print("========================================", flush=True)
    print("  VALIDATION COMPLETE", flush=True)
    print("========================================", flush=True)
    print(f"Locations: {loc_valid} valid / {loc_invalid} invalid", flush=True)
    print(f"Hourly PM2.5: {hourly_summary['valid_hourly_records']} valid / {hourly_summary['invalid_hourly_records']} invalid", flush=True)
    print(f"Missing values: {hourly_summary['missing_pm25_values']}", flush=True)
    print(f"Results saved in: {output_folder}", flush=True)


if __name__ == "__main__":
    main()
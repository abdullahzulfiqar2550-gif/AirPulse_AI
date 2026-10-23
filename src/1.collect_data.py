import os
import json
import sys
import time
import requests

from pathlib import Path
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv


# Windows terminal par UTF-8 encoding set karna
sys.stdout.reconfigure(encoding="utf-8")


# --------------------------------------------------
# Project Folders Setup
# --------------------------------------------------
SRC_FOLDER = Path(__file__).resolve().parent
PROJECT_FOLDER = SRC_FOLDER.parent
RAW_DATA_FOLDER = PROJECT_FOLDER / "raw_data"
ENV_FILE = PROJECT_FOLDER / ".env"

RAW_DATA_FOLDER.mkdir(exist_ok=True)


# --------------------------------------------------
# Settings (Sirf Pakistan "PK" ke liye)
# --------------------------------------------------
COUNTRY_CODE = "PK"
BASE_URL = "https://api.openaq.org/v3"
LOCATION_PAGE_SIZE = 100
RECORDS_PER_PAGE = 1000
MAX_PAGES_PER_SENSOR = 20
SLEEP_SECONDS = 1
MAX_RETRIES = 3

# 12-month window (October 2025 se ab tak ka data)
DATETIME_FROM = "2025-10-01T00:00:00Z"
DATETIME_TO = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# Pakistan ke official monitors + top low-cost sensors
MAX_LOWCOST_SENSORS = 15
MIN_HISTORY_DAYS = 180


# --------------------------------------------------
# Load API Key from .env
# --------------------------------------------------
load_dotenv(ENV_FILE)

API_KEY = os.getenv("OPENAQ_API_KEY")

if not API_KEY:
    raise ValueError("OPENAQ_API_KEY not found in .env file!")

headers = {
    "X-API-Key": API_KEY
}

print("=" * 50, flush=True)
print("AIRPULSE AI - PAKISTAN DATA COLLECTOR", flush=True)
print("=" * 50, flush=True)
print("API key loaded successfully", flush=True)
print("Country: Pakistan (PK)", flush=True)
print(f"Date window: {DATETIME_FROM} to {DATETIME_TO}", flush=True)


def parse_utc(text):
    """OpenAQ UTC timestamp ko datetime object mein convert karta hai."""
    if not text:
        return None
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def get_json_from_api(url, params):
    """API request bhejta hai aur rate-limit/errors par retry karta hai."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=60
            )

            # Agar rate limit (429) aye to 30 second wait karo
            if response.status_code == 429:
                print("  Rate limit hit. Waiting 30 seconds...", flush=True)
                time.sleep(30)
                continue

            # Server error par retry karo
            if response.status_code in (408, 500, 502, 503, 504):
                print(f"  Server error {response.status_code}. Retrying in 10s...", flush=True)
                time.sleep(10)
                continue

            if response.status_code != 200:
                print(f"  HTTP error {response.status_code}", flush=True)
                return None

            return response.json()

        except requests.RequestException as error:
            print(f"  Attempt {attempt}/{MAX_RETRIES} failed: {error}", flush=True)
            if attempt < MAX_RETRIES:
                print("  Waiting 10 seconds before retry...", flush=True)
                time.sleep(10)

    return None


def discover_pakistan_locations():
    """Pakistan ki tamam locations OpenAQ API (/v3/locations) se fetch karta hai."""
    print("\nStep 1: Discovering Pakistan locations...", flush=True)

    location_pages = []
    page_number = 1

    while True:
        print(f"  Downloading location page {page_number}...", flush=True)

        page_data = get_json_from_api(
            f"{BASE_URL}/locations",
            {
                "iso": COUNTRY_CODE,
                "limit": LOCATION_PAGE_SIZE,
                "page": page_number
            }
        )

        if page_data is None:
            print("  Could not download page. Stopping location discovery.", flush=True)
            break

        results = page_data.get("results", [])
        location_pages.append(page_data)
        print(f"  Got {len(results)} locations on this page", flush=True)

        if len(results) < LOCATION_PAGE_SIZE:
            break

        page_number += 1
        time.sleep(SLEEP_SECONDS)

    return location_pages


def find_pm25_sensors(location_pages):
    """Locations mein se sirf PM2.5 sensors dhoondta hai."""
    print("\nStep 2: Finding PM2.5 sensors in Pakistan...", flush=True)

    pm25_sensors = []
    seen_sensor_ids = set()

    for page_data in location_pages:
        locations = page_data.get("results", [])

        for location in locations:
            country = location.get("country") or {}

            # Strict check: sirf Pakistan ka data ho
            if country.get("code") != COUNTRY_CODE:
                continue

            datetime_first = (location.get("datetimeFirst") or {}).get("utc")
            datetime_last = (location.get("datetimeLast") or {}).get("utc")
            provider = location.get("provider") or {}

            for sensor in location.get("sensors") or []:
                parameter = sensor.get("parameter") or {}

                # Sirf PM2.5 filter karna
                if parameter.get("name") != "pm25":
                    continue

                sensor_id = sensor.get("id")
                if sensor_id in seen_sensor_ids:
                    continue

                seen_sensor_ids.add(sensor_id)

                first_dt = parse_utc(datetime_first)
                last_dt = parse_utc(datetime_last)
                history_days = 0

                if first_dt is not None and last_dt is not None:
                    history_days = (last_dt - first_dt).days

                pm25_sensors.append({
                    "sensor_id": sensor_id,
                    "location_id": location.get("id"),
                    "location_name": location.get("name"),
                    "parameter_id": parameter.get("id"),
                    "units": parameter.get("units"),
                    "is_monitor": location.get("isMonitor"),
                    "provider_name": provider.get("name"),
                    "datetime_first": datetime_first,
                    "datetime_last": datetime_last,
                    "history_days": history_days
                })

    print(f"Total location pages: {len(location_pages)}", flush=True)
    print(f"Total PM2.5 sensors found in Pakistan: {len(pm25_sensors)}", flush=True)
    return pm25_sensors


def choose_sensors(pm25_sensors):
    """Sare official monitors aur best low-cost sensors select karta hai."""
    print("\nStep 3: Selecting best sensors for download...", flush=True)

    window_start = parse_utc(DATETIME_FROM)
    monitors = []
    lowcost = []

    for sensor in pm25_sensors:
        if sensor["is_monitor"]:
            monitors.append(sensor)
            continue

        last_dt = parse_utc(sensor["datetime_last"])
        if last_dt is None or last_dt < window_start:
            continue

        if sensor["history_days"] < MIN_HISTORY_DAYS:
            continue

        lowcost.append(sensor)

    # Lambe arsay se chalne wale sensors ko pehle rakhein
    lowcost.sort(key=lambda item: item["history_days"], reverse=True)
    selected_lowcost = lowcost[:MAX_LOWCOST_SENSORS]

    selected = monitors + selected_lowcost

    print(f"  Official monitors: {len(monitors)}", flush=True)
    print(f"  Active low-cost sensors: {len(lowcost)}", flush=True)
    print(f"  Selected low-cost sensors: {len(selected_lowcost)}", flush=True)
    print(f"  Total sensors to download: {len(selected)}", flush=True)

    return selected


def sensor_date_window(sensor):
    """Har sensor ke liye sahi start aur end date tay karta hai."""
    last_dt = parse_utc(sensor["datetime_last"])
    window_start = parse_utc(DATETIME_FROM)

    if last_dt is not None and last_dt >= window_start:
        return DATETIME_FROM, DATETIME_TO

    if last_dt is None:
        return DATETIME_FROM, DATETIME_TO

    start_dt = last_dt - timedelta(days=365)
    return start_dt.strftime("%Y-%m-%dT%H:%M:%SZ"), last_dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def save_json(path, data, pretty=True):
    """JSON file save karne ka helper."""
    with open(path, "w", encoding="utf-8") as file:
        if pretty:
            json.dump(data, file, indent=2, ensure_ascii=False)
        else:
            json.dump(data, file, ensure_ascii=False)


def collect_hourly_pages(sensor_id, datetime_from, datetime_to):
    """Ek sensor ka ghante-war (/v3/sensors/{id}/hours) data fetch karta hai."""
    hourly_pages = []
    record_count = 0
    page_number = 1

    while page_number <= MAX_PAGES_PER_SENSOR:
        page_data = get_json_from_api(
            f"{BASE_URL}/sensors/{sensor_id}/hours",
            {
                "limit": RECORDS_PER_PAGE,
                "page": page_number,
                "datetime_from": datetime_from,
                "datetime_to": datetime_to
            }
        )

        if page_data is None:
            if hourly_pages:
                print("  Later page failed. Keeping already downloaded pages.", flush=True)
                return hourly_pages, record_count
            return None, 0

        hourly_pages.append(page_data)
        results = page_data.get("results", [])
        record_count += len(results)
        print(f"    Page {page_number}: {len(results)} records", flush=True)

        if len(results) < RECORDS_PER_PAGE:
            break

        page_number += 1
        time.sleep(SLEEP_SECONDS)

    return hourly_pages, record_count


def main():
    location_pages = discover_pakistan_locations()
    pm25_sensors = find_pm25_sensors(location_pages)
    selected_sensors = choose_sensors(pm25_sensors)

    # Naya timestamped folder create karega raw_data mein
    time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    collection_folder = RAW_DATA_FOLDER / f"pakistan_{time_str}"
    hourly_folder = collection_folder / "hourly"
    hourly_folder.mkdir(parents=True, exist_ok=True)

    locations_file = collection_folder / "openaq_pk_locations.json"
    save_json(
        locations_file,
        {
            "collected_at": datetime.now().isoformat(),
            "country_code": COUNTRY_CODE,
            "endpoint": "/v3/locations",
            "original_api_pages": location_pages
        }
    )
    print(f"\nLocations saved to: {locations_file.name}", flush=True)

    print("\nStep 4: Downloading hourly PM2.5 readings...", flush=True)

    successful_sensors = 0
    empty_sensors = 0
    failed_sensors = []
    total_hourly_records = 0

    for i, sensor in enumerate(selected_sensors):
        sensor_id = sensor["sensor_id"]
        dt_from, dt_to = sensor_date_window(sensor)

        print(
            f"\n[{i + 1}/{len(selected_sensors)}] "
            f"Sensor {sensor_id} | {sensor['location_name']}",
            flush=True
        )
        print(f"  Window: {dt_from} to {dt_to}", flush=True)

        hourly_pages, sensor_record_count = collect_hourly_pages(
            sensor_id, dt_from, dt_to
        )

        if hourly_pages is None:
            failed_sensors.append(sensor_id)
            print("  Failed. Skipping sensor.", flush=True)
            time.sleep(SLEEP_SECONDS)
            continue

        if sensor_record_count == 0:
            empty_sensors += 1
            print("  No records found in this date range.", flush=True)
        else:
            successful_sensors += 1
            total_hourly_records += sensor_record_count

        # Har sensor ki file alag save hogi
        save_json(
            hourly_folder / f"sensor_{sensor_id}.json",
            {
                "collected_at": datetime.now().isoformat(),
                "country_code": COUNTRY_CODE,
                "endpoint": f"/v3/sensors/{sensor_id}/hours",
                "sensor_id": sensor_id,
                "location_id": sensor["location_id"],
                "location_name": sensor["location_name"],
                "is_monitor": sensor["is_monitor"],
                "provider_name": sensor["provider_name"],
                "datetime_from": dt_from,
                "datetime_to": dt_to,
                "original_api_pages": hourly_pages
            },
            pretty=False
        )

        time.sleep(SLEEP_SECONDS)

    # Collection summary file
    summary_file = collection_folder / "collection_summary.json"
    summary = {
        "collected_at": datetime.now().isoformat(),
        "country_code": COUNTRY_CODE,
        "default_datetime_from": DATETIME_FROM,
        "default_datetime_to": DATETIME_TO,
        "location_pages": len(location_pages),
        "pm25_sensors_found": len(pm25_sensors),
        "pm25_sensors_selected": len(selected_sensors),
        "sensors_with_hourly_data": successful_sensors,
        "sensors_with_no_hourly_data": empty_sensors,
        "failed_sensors": failed_sensors,
        "total_hourly_records": total_hourly_records,
        "selected_sensor_ids": [item["sensor_id"] for item in selected_sensors],
        "locations_file": str(locations_file),
        "hourly_folder": str(hourly_folder)
    }
    save_json(summary_file, summary)

    print("\n" + "=" * 50, flush=True)
    print("PAKISTAN DATA COLLECTION COMPLETE!", flush=True)
    print("=" * 50, flush=True)
    print(f"Sensors selected: {len(selected_sensors)}", flush=True)
    print(f"Sensors with hourly data: {successful_sensors}", flush=True)
    print(f"Total hourly records: {total_hourly_records}", flush=True)
    print(f"Folder created: {collection_folder.name}", flush=True)


if __name__ == "__main__":
    main()
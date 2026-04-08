#!/usr/bin/env python3
"""
PiyoLog data preprocessor
Converts raw txt exports to anonymized CSV format
"""

import csv
import re
from datetime import datetime, timedelta
from pathlib import Path

# Constants
RAW_DATA_DIR = Path("raw_data")
OUTPUT_DIR = Path("processed_data")
DUMMY_BIRTH_DATE = datetime(2023, 1, 1)  # Anonymized birth date

# Event type mapping
EVENT_TYPES = {
    "Formula": "formula",
    "Breastfeeding": "breastfeeding",
    "Sleep": "sleep",
    "Wake-up": "wake_up",
    "Pee": "pee",
    "Poop": "poop",
    "Baths": "bath",
    "Drink": "drink",
    "Vomit": "vomit",
    "Weight": "weight",
    "Height": "height",
    "Head Size": "head_size",
    "Hospital": "hospital",
    "Others": "others",
}

# Events to skip
SKIP_EVENTS = {"Body Temp"}


def parse_date(date_str: str) -> datetime | None:
    """Parse date string like 'Sat, Jul 1, 2024'"""
    try:
        return datetime.strptime(date_str.strip(), "%a, %b %d, %Y")
    except ValueError:
        return None


def parse_duration(duration_str: str) -> int | None:
    """Parse duration like '2h 40m' to minutes"""
    match = re.match(r"(\d+)h\s*(\d+)m", duration_str)
    if match:
        hours, minutes = int(match.group(1)), int(match.group(2))
        return hours * 60 + minutes
    return None


def parse_milk_amount(text: str) -> int | None:
    """Extract milk amount in ml from text like 'Formula 100ml'"""
    match = re.search(r"(\d+)ml", text)
    if match:
        return int(match.group(1))
    return None


def parse_event_line(line: str) -> dict | None:
    """Parse an event line like '08:00 Formula 100ml comment'"""
    # Match time at start: HH:MM
    match = re.match(r"^(\d{2}:\d{2})\s+(.+)$", line.strip())
    if not match:
        return None

    time_str = match.group(1)
    rest = match.group(2)

    # Determine event type
    event_type = None
    for key, value in EVENT_TYPES.items():
        if rest.startswith(key):
            event_type = value
            break

    # Skip certain events
    for skip in SKIP_EVENTS:
        if rest.startswith(skip):
            return None

    if not event_type:
        return None

    # Extract milk amount for formula
    milk_amount = None
    if event_type == "formula":
        milk_amount = parse_milk_amount(rest)

    # Extract duration for wake_up
    duration_min = None
    if event_type == "wake_up":
        duration_match = re.search(r"\(([^)]+)\)", rest)
        if duration_match:
            duration_min = parse_duration(duration_match.group(1))

    return {
        "time": time_str,
        "event": event_type,
        "milk_amount": milk_amount,
        "sleep_minutes": duration_min,
    }


def collect_all_dates(filepath: Path) -> list[datetime]:
    """Collect all dates from a txt file"""
    dates = []
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    for day_block in content.split("----------"):
        for line in day_block.strip().split("\n"):
            parsed = parse_date(line)
            if parsed:
                dates.append(parsed)
                break
    return dates


def process_file(filepath: Path, birth_date: datetime) -> list[dict]:
    """Process a single txt file and return list of events"""
    events = []

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Split by day separator
    days = content.split("----------")

    for day_block in days:
        lines = day_block.strip().split("\n")
        if not lines:
            continue

        # Find date line (format: "Sat, Jul 1, 2024")
        current_date = None
        for line in lines:
            parsed_date = parse_date(line)
            if parsed_date:
                current_date = parsed_date
                break

        if not current_date:
            continue

        # Calculate day number from birth
        days_from_birth = (current_date - birth_date).days
        if days_from_birth < 0:
            continue

        dummy_date = DUMMY_BIRTH_DATE + timedelta(days=days_from_birth)

        # Parse event lines
        for line in lines:
            event = parse_event_line(line)
            if event:
                event["date"] = dummy_date.strftime("%Y-%m-%d")
                event["datetime"] = f"{dummy_date.strftime('%Y-%m-%d')} {event['time']}"
                event["days_from_birth"] = days_from_birth
                event["time"] = event.pop("time")
                events.append(event)

    return events


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Process all txt files
    txt_files = sorted(RAW_DATA_DIR.glob("*.txt"))
    print(f"Found {len(txt_files)} txt files")

    # Detect birth date as the earliest date across all files
    all_dates = []
    for filepath in txt_files:
        all_dates.extend(collect_all_dates(filepath))
    birth_date = min(all_dates)
    print(f"Detected birth date: {birth_date.strftime('%Y-%m-%d')}")

    all_events = []

    for filepath in txt_files:
        print(f"Processing {filepath.name}...")
        events = process_file(filepath, birth_date)
        all_events.extend(events)
        print(f"  -> {len(events)} events")

    # Sort by date and time
    all_events.sort(key=lambda x: x["datetime"])

    # Write to CSV
    output_path = OUTPUT_DIR / "piyolog.csv"
    fieldnames = [
        "date",
        "datetime",
        "days_from_birth",
        "time",
        "event",
        "milk_amount",
        "sleep_minutes",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_events)

    print(f"\nTotal events: {len(all_events)}")
    print(f"Output written to: {output_path}")


if __name__ == "__main__":
    main()

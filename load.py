import argparse
import json
import logging
import os
from datetime import datetime
from pathlib import Path

import psycopg
from dotenv import load_dotenv

from main import configure_logging
from transform import transform_snapshot


PROJECT_ROOT = Path(__file__).resolve().parent

logger = logging.getLogger(__name__)

# Pass values separately from SQL using named placeholders.
INSERT_SQL = """
INSERT INTO public.departure_observations (
    observed_at_utc,
    stop_id,
    stop_name,
    trip_id,
    route_short_name,
    headsign,
    scheduled_departure_utc,
    predicted_departure_utc,
    departure_delay_seconds,
    realtime,
    realtime_state,
    source_file
)
VALUES (
    %(observed_at_utc)s,
    %(stop_id)s,
    %(stop_name)s,
    %(trip_id)s,
    %(route_short_name)s,
    %(headsign)s,
    %(scheduled_departure_utc)s,
    %(predicted_departure_utc)s,
    %(departure_delay_seconds)s,
    %(realtime)s,
    %(realtime_state)s,
    %(source_file)s
)
ON CONFLICT ON CONSTRAINT uq_departure_observation
DO NOTHING;
"""


def get_database_settings():
    """Read connection settings without printing the password."""

    settings = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": os.getenv("DB_PORT", "5432"),
        "dbname": os.getenv("DB_NAME", "tampere_transport"),
        "user": os.getenv("DB_USER", "transport_user"),
        "password": os.getenv("DB_PASSWORD"),
        "connect_timeout": 10,
        "options": "-c timezone=UTC",
    }

    if not settings["password"]:
        raise ValueError("Missing DB_PASSWORD. Check your .env file.")

    return settings


def load_records(records, source_file, database_settings):
    """Load all records in one transaction."""

    inserted = 0

    # Commit when this block succeeds.
    # Roll back all inserts if an exception leaves the block.
    with psycopg.connect(**database_settings) as connection:
        with connection.cursor() as cursor:
            for record in records:
                # Copy the record so we do not modify the original.
                values = dict(record)
                values["source_file"] = source_file

                # Convert timestamp strings into Python datetime objects.
                for field in (
                    "observed_at_utc",
                    "scheduled_departure_utc",
                    "predicted_departure_utc",
                ):
                    if values[field] is not None:
                        values[field] = datetime.fromisoformat(values[field])

                cursor.execute(INSERT_SQL, values)

                # INSERT gives 1 for a new row and 0 for a skipped duplicate.
                inserted += cursor.rowcount

    # Only report committed results.
    skipped = len(records) - inserted
    return inserted, skipped


def main():
    """Validate and load a selected raw snapshot."""

    parser = argparse.ArgumentParser(
        description="Load a raw departure snapshot into PostgreSQL."
    )

    parser.add_argument(
        "snapshot",
        type=Path,
        help="Path to a raw JSON snapshot",
    )

    args = parser.parse_args()

    configure_logging()
    load_dotenv(PROJECT_ROOT / ".env")

    try:
        logger.info("Loading snapshot: %s", args.snapshot.name)

        with args.snapshot.open(encoding="utf-8") as file:
            snapshot = json.load(file)

        # Reuse our validation and transformation rules.
        records = transform_snapshot(snapshot)
        logger.info("Validated %s departure records", len(records))

        database_settings = get_database_settings()

        inserted, skipped = load_records(
            records,
            args.snapshot.name,
            database_settings,
        )

        logger.info(
            "Load committed: inserted=%s, duplicates_skipped=%s",
            inserted,
            skipped,
        )

        return 0

    except (OSError, ValueError, psycopg.Error) as error:
        logger.error("Load failed: %s", error)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
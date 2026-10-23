import json
import logging
import os
from datetime import datetime, timezone

import psycopg
import requests
from dotenv import load_dotenv

from main import (
    PROJECT_ROOT,
    configure_logging,
    fetch_departures,
    save_raw_snapshot,
)
from transform import transform_snapshot
from load import get_database_settings, load_records


logger = logging.getLogger(__name__)


def main():
    """Collect, save, validate, transform and load one snapshot."""

    configure_logging()
    logger.info("Pipeline started")

    try:
        # 1. Read configuration without displaying credentials.
        load_dotenv(PROJECT_ROOT / ".env")
        api_key = os.getenv("DIGITRANSIT_API_KEY", "").strip()

        if not api_key:
            raise RuntimeError(
                "Missing DIGITRANSIT_API_KEY. Check your .env file."
            )

        # 2. Collect departures and record the collection interval.
        requested_at = datetime.now(timezone.utc)
        payload = fetch_departures(api_key)
        received_at = datetime.now(timezone.utc)

        # 3. Save the response and keep its exact file path.
        snapshot_path = save_raw_snapshot(
            payload,
            requested_at,
            received_at,
        )
        logger.info("Raw snapshot saved to: %s", snapshot_path)

        # 4. Read the exact snapshot saved during this run.
        with snapshot_path.open(encoding="utf-8") as file:
            snapshot = json.load(file)

        # 5. Validate the snapshot and build flat departure records.
        records = transform_snapshot(snapshot)
        logger.info(
            "Validated and transformed %s departures",
            len(records),
        )

        # 6. Load those records into PostgreSQL.
        database_settings = get_database_settings()

        inserted, skipped = load_records(
            records,
            snapshot_path.name,
            database_settings,
        )

        logger.info(
            "Load committed: inserted=%s, duplicates_skipped=%s",
            inserted,
            skipped,
        )
        logger.info("Pipeline finished successfully")
        return 0

    except (
        requests.exceptions.RequestException,
        RuntimeError,
        OSError,
        ValueError,
        psycopg.Error,
    ) as error:
        logger.error("Pipeline failed: %s", error)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
import json
import logging
import os
from datetime import datetime, timezone
from uuid import uuid4

import psycopg
from dotenv import load_dotenv

from main import (
    PROJECT_ROOT,
    configure_logging,
    fetch_departures,
    save_raw_snapshot,
)
from transform import transform_snapshot
from load import get_database_settings, load_records
from run_tracking import start_run, update_run_stage, finish_run


logger = logging.getLogger(__name__)


def main():
    """Collect and load one snapshot, recording execution progress."""

    configure_logging()

    run_id = uuid4()
    started_at = datetime.now(timezone.utc)

    database_settings = None
    tracking_started = False
    stage = "configuration"
    records_validated = None

    logger.info("Pipeline started: run_id=%s", run_id)

    try:
        # Read settings and create the run record.
        load_dotenv(PROJECT_ROOT / ".env")
        database_settings = get_database_settings()

        start_run(run_id, started_at, database_settings)
        tracking_started = True

        api_key = os.getenv("DIGITRANSIT_API_KEY", "").strip()

        if not api_key:
            raise RuntimeError(
                "Missing DIGITRANSIT_API_KEY. Check your .env file."
            )

        # Collect departures.
        stage = "collection"
        update_run_stage(run_id, stage, database_settings)

        requested_at = datetime.now(timezone.utc)
        payload = fetch_departures(api_key)
        received_at = datetime.now(timezone.utc)

        # Save this run's raw snapshot.
        stage = "saving"
        update_run_stage(run_id, stage, database_settings)

        snapshot_path = save_raw_snapshot(
            payload,
            requested_at,
            received_at,
        )
        logger.info("Raw snapshot saved to: %s", snapshot_path)

        # Read, validate and transform the exact saved snapshot.
        stage = "validation"
        update_run_stage(
            run_id,
            stage,
            database_settings,
            source_file=snapshot_path.name,
        )

        with snapshot_path.open(encoding="utf-8") as file:
            snapshot = json.load(file)

        records = transform_snapshot(snapshot)
        records_validated = len(records)

        logger.info(
            "Validated and transformed %s departures",
            records_validated,
        )

        # Load observations using the existing transaction.
        stage = "loading"
        update_run_stage(run_id, stage, database_settings)

        inserted, skipped = load_records(
            records,
            snapshot_path.name,
            database_settings,
        )

    except Exception as error:
        # Record only the exception class, avoiding sensitive error text.
        error_type = type(error).__name__

        logger.error(
            "Pipeline failed: run_id=%s, stage=%s, error_type=%s",
            run_id,
            stage,
            error_type,
        )

        if tracking_started:
            try:
                finish_run(
                    run_id=run_id,
                    finished_at=datetime.now(timezone.utc),
                    status="failed",
                    stage=stage,
                    database_settings=database_settings,
                    records_validated=records_validated,
                    error_type=error_type,
                )

            except (psycopg.Error, RuntimeError, ValueError) as tracking_error:
                logger.error(
                    "Could not record failure: run_id=%s, error_type=%s",
                    run_id,
                    type(tracking_error).__name__,
                )

        return 1

    # load_records() has returned, so the observations have committed.
    logger.info(
        "Load committed: inserted=%s, duplicates_skipped=%s",
        inserted,
        skipped,
    )

    try:
        finish_run(
            run_id=run_id,
            finished_at=datetime.now(timezone.utc),
            status="succeeded",
            stage="complete",
            database_settings=database_settings,
            records_validated=records_validated,
            records_inserted=inserted,
            duplicates_skipped=skipped,
        )

    except (psycopg.Error, RuntimeError, ValueError) as error:
        logger.error(
            "Observations committed, but success tracking failed: "
            "run_id=%s, error_type=%s",
            run_id,
            type(error).__name__,
        )
        return 1

    logger.info("Pipeline finished successfully: run_id=%s", run_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
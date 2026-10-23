import os
import unittest
from uuid import uuid4

import psycopg
from dotenv import load_dotenv

from load import PROJECT_ROOT, get_database_settings, load_records


@unittest.skipUnless(
    os.getenv("RUN_DB_TESTS") == "1",
    "Set RUN_DB_TESTS=1 to run local PostgreSQL tests.",
)
class TestDatabaseRollback(unittest.TestCase):
    def test_failed_batch_leaves_no_rows(self):
        load_dotenv(PROJECT_ROOT / ".env")
        settings = get_database_settings()

        # A unique label keeps test data separate from real snapshots.
        test_id = uuid4().hex
        source_file = f"rollback_test_{test_id}.json"

        first_record = {
            "observed_at_utc": "2026-10-23T12:00:00+00:00",
            "stop_id": "test:rollback",
            "stop_name": "Rollback test stop",
            "trip_id": f"test:{test_id}:1",
            "route_short_name": "TEST",
            "headsign": None,
            "scheduled_departure_utc": "2026-10-23T12:05:00+00:00",
            "predicted_departure_utc": None,
            "departure_delay_seconds": None,
            "realtime": False,
            "realtime_state": "SCHEDULED",
        }

        second_record = dict(first_record)
        second_record["trip_id"] = f"test:{test_id}:2"

        # Deliberately violate stop_name's NOT NULL constraint.
        second_record["stop_name"] = None

        try:
            with self.assertRaises(
                psycopg.errors.NotNullViolation
            ) as caught:
                load_records(
                    [first_record, second_record],
                    source_file,
                    settings,
                )

            self.assertEqual(
                caught.exception.diag.column_name,
                "stop_name",
            )

            # Use a new connection to check committed database contents.
            with psycopg.connect(**settings) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT COUNT(*)
                        FROM public.departure_observations
                        WHERE source_file = %s
                        """,
                        (source_file,),
                    )
                    remaining = cursor.fetchone()[0]

            self.assertEqual(
                remaining,
                0,
                "A failed batch left partially committed rows.",
            )

        finally:
            # Remove only this test's rows if rollback is ever broken.
            with psycopg.connect(**settings) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        DELETE FROM public.departure_observations
                        WHERE source_file = %s
                        """,
                        (source_file,),
                    )


if __name__ == "__main__":
    unittest.main()
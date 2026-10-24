import unittest
from unittest.mock import patch
from uuid import UUID

import pipeline


class TestPipelineFailure(unittest.TestCase):
    @patch("pipeline.configure_logging")
    @patch("pipeline.load_dotenv")
    @patch("pipeline.get_database_settings")
    @patch("pipeline.start_run")
    @patch("pipeline.update_run_stage")
    @patch("pipeline.fetch_departures")
    @patch("pipeline.save_raw_snapshot")
    @patch("pipeline.load_records")
    @patch("pipeline.finish_run")
    @patch("pipeline.os.getenv", return_value="test-key")
    def test_collection_failure_is_recorded(
        self,
        getenv,
        finish_run,
        load_records,
        save_raw_snapshot,
        fetch_departures,
        update_run_stage,
        start_run,
        get_database_settings,
        load_dotenv,
        configure_logging,
    ):
        settings = {"test": "settings"}
        get_database_settings.return_value = settings

        # Simulate an exhausted collection failure.
        fetch_departures.side_effect = RuntimeError(
            "Simulated collection failure"
        )

        with self.assertLogs("pipeline", level="ERROR"):
            exit_code = pipeline.main()

        self.assertEqual(exit_code, 1)

        start_run.assert_called_once()
        run_id, started_at, used_settings = start_run.call_args.args

        self.assertIsInstance(run_id, UUID)
        self.assertIsNotNone(started_at.tzinfo)
        self.assertEqual(used_settings, settings)

        update_run_stage.assert_called_once_with(
            run_id,
            "collection",
            settings,
        )

        finish_run.assert_called_once()
        outcome = finish_run.call_args.kwargs

        self.assertEqual(outcome["run_id"], run_id)
        self.assertEqual(outcome["status"], "failed")
        self.assertEqual(outcome["stage"], "collection")
        self.assertEqual(outcome["error_type"], "RuntimeError")
        self.assertIsNone(outcome["records_validated"])

        save_raw_snapshot.assert_not_called()
        load_records.assert_not_called()


if __name__ == "__main__":
    unittest.main()
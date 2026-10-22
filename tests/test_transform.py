import unittest

from transform import departure_to_utc, transform_snapshot


class TestTransformSnapshot(unittest.TestCase):
    def setUp(self):
        # Small invented dataset with easy-to-check timestamps.
        self.snapshot = {
            "metadata": {
                "stop_id": "tampere:0835",
                "received_at_utc": "2026-10-21T12:00:00+00:00",
            },
            "response": {
                "data": {
                    "stop": {
                        "gtfsId": "tampere:0835",
                        "name": "Hervannan kampus A",
                        "stoptimesWithoutPatterns": [
                            {
                                "serviceDay": 0,
                                "scheduledDeparture": 3600,
                                "realtimeDeparture": 3662,
                                "departureDelay": 62,
                                "realtime": True,
                                "realtimeState": "UPDATED",
                                "headsign": "Sorin aukio",
                                "trip": {
                                    "gtfsId": "tampere:test-trip",
                                    "route": {"shortName": "3"},
                                },
                            }
                        ],
                    }
                }
            },
        }

    def departure(self):
        return self.snapshot["response"]["data"]["stop"][
            "stoptimesWithoutPatterns"
        ][0]

    def test_realtime_departure_is_transformed(self):
        records = transform_snapshot(self.snapshot)

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["trip_id"], "tampere:test-trip")
        self.assertEqual(records[0]["departure_delay_seconds"], 62)
        self.assertEqual(
            records[0]["scheduled_departure_utc"],
            "1970-01-01T01:00:00+00:00",
        )
        self.assertEqual(
            records[0]["predicted_departure_utc"],
            "1970-01-01T01:01:02+00:00",
        )

    def test_timetable_only_departure_has_unknown_live_values(self):
        self.departure()["realtime"] = False
        self.departure()["realtimeState"] = "SCHEDULED"
        self.departure()["realtimeDeparture"] = 3600
        self.departure()["departureDelay"] = 0

        record = transform_snapshot(self.snapshot)[0]

        self.assertIsNone(record["predicted_departure_utc"])
        self.assertIsNone(record["departure_delay_seconds"])

    def test_missing_trip_id_is_rejected(self):
        del self.departure()["trip"]["gtfsId"]

        with self.assertRaisesRegex(ValueError, "Invalid departure 1"):
            transform_snapshot(self.snapshot)

    def test_inconsistent_delay_is_rejected(self):
        self.departure()["departureDelay"] = 999

        with self.assertRaisesRegex(ValueError, "does not match"):
            transform_snapshot(self.snapshot)

    def test_departure_after_midnight_is_supported(self):
        self.assertEqual(
            departure_to_utc(0, 90000),
            "1970-01-02T01:00:00+00:00",
        )


if __name__ == "__main__":
    unittest.main()
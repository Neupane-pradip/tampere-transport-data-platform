import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"


def require_text(value, field_name):
    """Require a non-empty string."""

    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")

    return value


def require_integer(value, field_name, minimum=None):
    """Require an integer. Reject booleans, floats and strings."""

    # In Python, bool is a subclass of int, so check the exact type.
    if type(value) is not int:
        raise ValueError(f"{field_name} must be an integer.")

    if minimum is not None and value < minimum:
        raise ValueError(f"{field_name} must be at least {minimum}.")

    return value


def departure_to_utc(service_day, seconds):
    """Convert service-day seconds into a full UTC timestamp."""

    # Values above 86400 are allowed for departures after midnight.
    timestamp = service_day + seconds

    return datetime.fromtimestamp(
        timestamp,
        tz=timezone.utc,
    ).isoformat()


def transform_snapshot(snapshot):
    """Validate a raw snapshot and return flat departure records."""

    if not isinstance(snapshot, dict):
        raise ValueError("Snapshot must be a JSON object.")

    try:
        metadata = snapshot["metadata"]
        stop = snapshot["response"]["data"]["stop"]

        observed_at = require_text(
            metadata["received_at_utc"],
            "received_at_utc",
        )

        # Make sure the collection time includes a timezone.
        observed_datetime = datetime.fromisoformat(observed_at)

        if observed_datetime.tzinfo is None:
            raise ValueError("received_at_utc must include a timezone.")

        observed_at = observed_datetime.astimezone(
            timezone.utc
        ).isoformat()

        stop_id = require_text(stop["gtfsId"], "stop_id")
        stop_name = require_text(stop["name"], "stop_name")

        if stop_id != metadata["stop_id"]:
            raise ValueError("Response stop ID does not match metadata.")

        departures = stop["stoptimesWithoutPatterns"]

        if not isinstance(departures, list):
            raise ValueError("Departures must be a list.")

        records = []

        for index, departure in enumerate(departures, start=1):
            try:
                service_day = require_integer(
                    departure["serviceDay"],
                    "serviceDay",
                    minimum=0,
                )

                scheduled_seconds = require_integer(
                    departure["scheduledDeparture"],
                    "scheduledDeparture",
                    minimum=0,
                )

                realtime = departure["realtime"]

                if type(realtime) is not bool:
                    raise ValueError("realtime must be true or false.")

                realtime_state = require_text(
                    departure["realtimeState"],
                    "realtimeState",
                )

                trip_id = require_text(
                    departure["trip"]["gtfsId"],
                    "trip_id",
                )

                route_short_name = require_text(
                    departure["trip"]["route"]["shortName"],
                    "route_short_name",
                )

                # A destination description can be missing.
                headsign = departure.get("headsign")

                if headsign is not None and not isinstance(headsign, str):
                    raise ValueError("headsign must be a string or null.")

                # Timetable-only departures have unknown live values.
                predicted_departure = None
                delay_seconds = None

                if realtime:
                    realtime_seconds = require_integer(
                        departure["realtimeDeparture"],
                        "realtimeDeparture",
                        minimum=0,
                    )

                    # Negative delays are valid: the prediction is early.
                    delay_seconds = require_integer(
                        departure["departureDelay"],
                        "departureDelay",
                    )

                    if delay_seconds != realtime_seconds - scheduled_seconds:
                        raise ValueError(
                            "departureDelay does not match departure times."
                        )

                    predicted_departure = departure_to_utc(
                        service_day,
                        realtime_seconds,
                    )

                records.append(
                    {
                        "observed_at_utc": observed_at,
                        "stop_id": stop_id,
                        "stop_name": stop_name,
                        "trip_id": trip_id,
                        "route_short_name": route_short_name,
                        "headsign": headsign,
                        "scheduled_departure_utc": departure_to_utc(
                            service_day,
                            scheduled_seconds,
                        ),
                        "predicted_departure_utc": predicted_departure,
                        "departure_delay_seconds": delay_seconds,
                        "realtime": realtime,
                        "realtime_state": realtime_state,
                    }
                )

            except (KeyError, TypeError, ValueError, OverflowError) as error:
                raise ValueError(
                    f"Invalid departure {index}: {error}"
                ) from error

        return records

    except (KeyError, TypeError) as error:
        raise ValueError(
            f"Snapshot structure is missing or invalid: {error}"
        ) from error


def main():
    """Transform the snapshot selected on the command line."""

    parser = argparse.ArgumentParser(
        description="Validate and transform a raw departure snapshot."
    )

    parser.add_argument(
        "snapshot",
        type=Path,
        help="Path to a raw JSON snapshot",
    )

    args = parser.parse_args()

    with args.snapshot.open(encoding="utf-8") as file:
        snapshot = json.load(file)

    # Validate everything before writing a processed file.
    records = transform_snapshot(snapshot)

    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    output_path = PROCESSED_DATA_DIR / args.snapshot.name

    # Reprocessing the same source replaces its derived output.
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(records, file, indent=2, ensure_ascii=False)
        file.write("\n")

    print(f"Validated and transformed {len(records)} departures.")
    print(f"Processed file saved to: {output_path}")


if __name__ == "__main__":
    main()
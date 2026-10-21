import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv


# Keep paths relative to this file.
PROJECT_ROOT = Path(__file__).resolve().parent
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
LOG_DIR = PROJECT_ROOT / "logs"

API_URL = "https://api.digitransit.fi/routing/v2/waltti/gtfs/v1"

# Three attempts means the first request plus up to two retries.
MAX_ATTEMPTS = 3
BACKOFF_SECONDS = 2

# Retry only these temporary server errors.
RETRYABLE_STATUS_CODES = {500, 502, 503, 504}

logger = logging.getLogger(__name__)

QUERY = """
{
  stop(id: "tampere:0835") {
    gtfsId
    name
    stoptimesWithoutPatterns(numberOfDepartures: 5) {
      serviceDay
      scheduledDeparture
      realtimeDeparture
      departureDelay
      realtime
      realtimeState
      headsign
      trip {
        gtfsId
        route {
          shortName
        }
      }
    }
  }
}
"""


def configure_logging():
    """Write logs to both the terminal and a local file."""

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Display log timestamps in UTC.
    logging.Formatter.converter = time.gmtime

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)sZ | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(
                LOG_DIR / "pipeline.log",
                encoding="utf-8",
            ),
        ],
    )


def fetch_departures(api_key):
    """Fetch departures, retrying selected temporary failures."""

    for attempt in range(1, MAX_ATTEMPTS + 1):
        logger.info("API attempt %s/%s", attempt, MAX_ATTEMPTS)

        try:
            response = requests.post(
                API_URL,
                headers={
                    "digitransit-subscription-key": api_key,
                },
                json={"query": QUERY},
                # Connection timeout, then read inactivity timeout.
                timeout=(10, 30),
            )

            response.raise_for_status()

        except requests.exceptions.SSLError:
            # Certificate problems need investigation.
            # SSLError is a ConnectionError subclass, so catch it first.
            raise

        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
        ) as error:
            # Log the error type, never request headers or the key.
            reason = type(error).__name__

        except requests.exceptions.HTTPError as error:
            status_code = error.response.status_code

            if status_code not in RETRYABLE_STATUS_CODES:
                # Authentication errors and rate limits stop here.
                raise

            reason = f"HTTP {status_code}"
            error.response.close()

        else:
            # This block runs only when the HTTP request succeeds.
            # JSON and GraphQL problems are not retried.
            payload = response.json()

            if not isinstance(payload, dict):
                raise RuntimeError("Expected a JSON object from the API.")

            if payload.get("errors"):
                raise RuntimeError(
                    "GraphQL returned errors:\n"
                    + json.dumps(
                        payload["errors"],
                        indent=2,
                        ensure_ascii=False,
                    )
                )

            data = payload.get("data")

            if not isinstance(data, dict) or data.get("stop") is None:
                raise RuntimeError(
                    "The API did not return the requested stop."
                )

            logger.info("API request succeeded")
            return payload

        # Failed attempts reach this point.
        if attempt == MAX_ATTEMPTS:
            raise RuntimeError(
                f"API request failed after {MAX_ATTEMPTS} attempts: "
                f"{reason}"
            )

        # Wait 2 seconds after attempt 1, then 4 after attempt 2.
        wait_seconds = BACKOFF_SECONDS * (2 ** (attempt - 1))

        logger.warning(
            "%s. Retrying in %s seconds",
            reason,
            wait_seconds,
        )

        time.sleep(wait_seconds)


def save_raw_snapshot(payload, requested_at, received_at):
    """Save a successful response and its collection metadata."""

    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = received_at.strftime("%Y%m%dT%H%M%S_%fZ")
    file_path = RAW_DATA_DIR / f"departures_tampere_0835_{timestamp}.json"

    snapshot = {
        "metadata": {
            "source": "digitransit",
            "endpoint": API_URL,
            "stop_id": "tampere:0835",
            # This interval includes any retry attempts and waits.
            "requested_at_utc": requested_at.isoformat(),
            "received_at_utc": received_at.isoformat(),
            "query": QUERY,
        },
        "response": payload,
    }

    # Refuse to overwrite an existing snapshot.
    with file_path.open("x", encoding="utf-8") as file:
        json.dump(snapshot, file, indent=2, ensure_ascii=False)
        file.write("\n")

    return file_path


def main():
    """Run one collection and return its exit code."""

    configure_logging()
    logger.info("Pipeline started")

    try:
        load_dotenv(PROJECT_ROOT / ".env")
        api_key = os.getenv("DIGITRANSIT_API_KEY", "").strip()

        if not api_key:
            raise RuntimeError(
                "Missing DIGITRANSIT_API_KEY. Check your .env file."
            )

        requested_at = datetime.now(timezone.utc)
        payload = fetch_departures(api_key)
        received_at = datetime.now(timezone.utc)

        file_path = save_raw_snapshot(
            payload,
            requested_at,
            received_at,
        )

        logger.info("Raw snapshot saved to: %s", file_path)
        logger.info("Pipeline finished successfully")
        return 0

    except (
        requests.exceptions.RequestException,
        RuntimeError,
        OSError,
    ) as error:
        logger.error("Pipeline failed: %s", error)
        return 1


if __name__ == "__main__":
    # Exit code 0 means success; 1 means failure.
    raise SystemExit(main())
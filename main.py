import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv


# Find the project folder, regardless of where Python is run from.
PROJECT_ROOT = Path(__file__).resolve().parent

# Store collected API responses here.
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"

# Digitransit's Waltti GraphQL endpoint.
API_URL = "https://api.digitransit.fi/routing/v2/waltti/gtfs/v1"

# Request the next five departures from Hervannan kampus A.
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


def fetch_departures(api_key):
    """Request departures and check the API response."""

    # Send the key in a header and the query in the JSON body.
    response = requests.post(
        API_URL,
        headers={
            "digitransit-subscription-key": api_key,
        },
        json={"query": QUERY},
        timeout=30,
    )

    # Stop if the server returns an HTTP error.
    response.raise_for_status()

    # Convert the JSON response into Python dictionaries and lists.
    payload = response.json()

    # GraphQL can return query errors even when HTTP succeeds.
    if payload.get("errors"):
        raise RuntimeError(
            "GraphQL returned errors:\n"
            + json.dumps(payload["errors"], indent=2, ensure_ascii=False)
        )

    # Check that the requested stop exists in the response.
    if payload.get("data", {}).get("stop") is None:
        raise RuntimeError("The API did not return the requested stop.")

    return payload


def save_raw_snapshot(payload, requested_at, received_at):
    """Save the API response together with collection information."""

    # Create data/raw if it does not already exist.
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Use a UTC timestamp with microseconds to distinguish runs.
    timestamp = received_at.strftime("%Y%m%dT%H%M%S_%fZ")
    file_path = RAW_DATA_DIR / f"departures_tampere_0835_{timestamp}.json"

    # Keep collection details separate from the original response.
    # Never include the API key.
    snapshot = {
        "metadata": {
            "source": "digitransit",
            "endpoint": API_URL,
            "stop_id": "tampere:0835",
            "requested_at_utc": requested_at.isoformat(),
            "received_at_utc": received_at.isoformat(),
            "query": QUERY,
        },
        "response": payload,
    }

    # "x" creates a new file and refuses to overwrite an existing one.
    # UTF-8 preserves Finnish characters.
    with file_path.open("x", encoding="utf-8") as file:
        json.dump(snapshot, file, indent=2, ensure_ascii=False)
        file.write("\n")

    return file_path


def main():
    """Load settings, fetch departures, and save a snapshot."""

    # Read private settings from the project's .env file.
    load_dotenv(PROJECT_ROOT / ".env")

    api_key = os.getenv("DIGITRANSIT_API_KEY", "").strip()

    # Stop before making a request if the key is missing.
    if not api_key:
        raise RuntimeError(
            "Missing DIGITRANSIT_API_KEY. Add your key to the .env file."
        )

    print("Requesting departures for Hervannan kampus A...")

    # Record when the request starts and when its result is available.
    requested_at = datetime.now(timezone.utc)
    payload = fetch_departures(api_key)
    received_at = datetime.now(timezone.utc)

    file_path = save_raw_snapshot(
        payload,
        requested_at,
        received_at,
    )

    # Display the result so we can inspect it while learning.
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"\nRaw snapshot saved to: {file_path}")


# Run the program only when this file is executed directly.
if __name__ == "__main__":
    main()
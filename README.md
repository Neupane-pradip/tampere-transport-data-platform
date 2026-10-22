# Tampere Public Transport Data Platform

A data engineering learning project using Tampere public transport data
from Digitransit.

I am building this project step by step to learn how to collect,
validate, transform and store data from a real API.

The starting point is tram departures from **Hervannan kampus A**
in Tampere.

## Current functionality

- Fetches the next five departures from the selected stop.
- Collects timetable information and available real-time predictions.
- Uses an API key stored outside source code.
- Retries selected temporary connection and server failures.
- Writes operational logs to the terminal and a log file.
- Saves successful responses as timestamped raw JSON snapshots.
- Validates and transforms saved snapshots into flat departure records.
- Includes automated tests for ingestion and transformation behaviour.

## Tools

- Python 3.13
- Requests
- python-dotenv
- GraphQL
- JSON
- Python unittest
- Git and GitHub

## Project files

| File or folder | Purpose |
|---|---|
| `main.py` | Fetch departures and save raw snapshots |
| `transform.py` | Validate and transform a saved snapshot |
| `tests/test_main.py` | Test ingestion and retry behaviour |
| `tests/test_transform.py` | Test validation and transformation |
| `requirements.txt` | Required Python packages |
| `.env.example` | Example configuration without credentials |
| `.env` | Private local API key; ignored by Git |
| `data/raw/` | Collected API snapshots; ignored by Git |
| `data/processed/` | Transformed records; ignored by Git |
| `logs/` | Local pipeline logs; ignored by Git |

## Setup

Run these commands in PowerShell from the project folder.

### 1. Create a virtual environment

```powershell
python -m venv .venv
```

### 2. Activate it

```powershell
.\.venv\Scripts\Activate.ps1
```

If your PyCharm terminal already shows `(.venv)`, the environment
is already active.

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Configure the API key

Register and subscribe through the
[Digitransit developer portal](https://portal-api.digitransit.fi/)
to obtain an API key.

For the first setup, copy the example configuration:

```powershell
Copy-Item .env.example .env
```

Open `.env` and enter your key:

```dotenv
DIGITRANSIT_API_KEY=your_api_key
```

Keep the actual key private. Never commit `.env` to GitHub.

You can check that Git ignores it:

```powershell
git check-ignore .env
```

## Collect departures

```powershell
python main.py
```

The program logs its progress and saves a successful response under:

```text
data/raw/
```

Example filename:

```text
departures_tampere_0835_20261021T120913_514983Z.json
```

Each snapshot contains:

- `metadata`: source, endpoint, stop ID, query and UTC collection times.
- `response`: the API response without transformations.

Each successful run creates a separate snapshot.

The program currently requests stop `tampere:0835`.
The endpoint and query are defined in `main.py`.

## Reliability and logging

The collector makes up to three attempts for:

- Connection failures, except SSL certificate errors.
- Timeouts.
- HTTP 500, 502, 503 and 504 responses.

It waits 2 seconds before the second attempt and 4 seconds before
the third attempt.

Authentication errors, rate limits, invalid JSON and GraphQL errors
stop the run.

Logs are written to the terminal and:

```text
logs/pipeline.log
```

Log timestamps use UTC.

- `INFO`: normal progress.
- `WARNING`: a temporary failure before a retry.
- `ERROR`: a failed run.

A successful run exits with code `0`.
A handled failure exits with code `1`.

Check the exit code immediately after running the program:

```powershell
$LASTEXITCODE
```

View recent logs:

```powershell
Get-Content .\logs\pipeline.log -Tail 15
```

## Validate and transform a snapshot

Use the filename of an existing raw snapshot:

```powershell
python transform.py data/raw/YOUR_SNAPSHOT_FILENAME.json
```

Replace `YOUR_SNAPSHOT_FILENAME.json` with the actual filename.

The transformation creates one flat record per departure under:

```text
data/processed/
```

The output uses the same filename as the raw snapshot.
Reprocessing the same snapshot replaces its processed output.

Validation checks include:

- Required fields and expected data types.
- Matching stop IDs in metadata and the API response.
- A collection timestamp containing a timezone.
- Consistency between real-time departure and delay values.

Invalid data stops processing before a new output is written.
The raw snapshot remains unchanged.

### Transformed fields

| Field | Meaning |
|---|---|
| `observed_at_utc` | When the collection result became available |
| `stop_id` | Stop identifier |
| `stop_name` | Stop name |
| `trip_id` | Specific journey identifier |
| `route_short_name` | Line number or short label |
| `headsign` | Destination text, when available |
| `scheduled_departure_utc` | Timetable departure timestamp |
| `predicted_departure_utc` | Real-time departure timestamp, when available |
| `departure_delay_seconds` | Predicted delay, when available |
| `realtime` | Whether real-time information is available |
| `realtime_state` | Status supplied by the API |

## Understanding the data

A route can have several patterns, representing different directions
or stop sequences. A trip is a specific journey.

Departure values are seconds from the service day's midnight.
Adding a departure value to `serviceDay` gives its Unix timestamp.

Departure seconds can exceed 86400 for journeys continuing after midnight.

Real-time departure values are predictions. They do not confirm when
a vehicle actually departed.

When `realtime` is false, the transformation sets predicted departure
and live delay to `null`. A timetable-only delay of zero is not evidence
that a vehicle is on time.

Cancellation status is preserved in `realtime_state` when supplied.
It must be considered before interpreting departure predictions.

Collection timestamps describe when this program collected data.
They do not identify when the provider originally generated a prediction.

## Run tests

```powershell
python -m unittest discover -s tests -v
```

The tests use simulated responses and do not require a real API key
or network connection.

They check selected behaviours, including:

- Retrying temporary failures.
- Stopping after the attempt limit.
- Avoiding retries for authentication, rate-limit and GraphQL errors.
- Converting departures into structured records.
- Representing unavailable live values as null.
- Rejecting missing identifiers and inconsistent delays.
- Handling departure times after midnight.

Passing tests cover these scenarios, not every possible failure.

## What I am learning

- API authentication and HTTP requests
- GraphQL queries and JSON responses
- Public transport routes, patterns, stops and trips
- Environment variables and secret handling
- Retries, backoff and logging
- Raw snapshots and collection metadata
- Data validation and transformation
- UTC timestamps and missing values
- Automated testing with mocks

## AI assistance

I use ChatGPT and Codex as learning assistants for explanations,
code suggestions, debugging, tests and documentation.

I build and run the project step by step, review the suggestions
and use the results to develop my own understanding.

## Planned next steps

- PostgreSQL storage for departure observations
- Repeatable database loading
- SQL transformations and data-quality checks
- Scheduled collection and monitoring
- Reports on predicted delays and real-time data availability

## Data source

This project uses the Digitransit Waltti Routing API.

- [Routing API documentation](https://digitransit.fi/en/developers/apis/1-routing-api/)
- [Developer portal](https://portal-api.digitransit.fi/)
- [Terms of use](https://digitransit.fi/en/developers/apis/7-terms-of-use/)

This is an independent learning project and is not an official
Nysse or Digitransit service.
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
- Uses credentials stored outside source code.
- Retries selected temporary connection and server failures.
- Writes operational logs with UTC timestamps.
- Saves successful responses as timestamped raw JSON snapshots.
- Validates and transforms snapshots into flat departure records.
- Loads departure observations into local PostgreSQL.
- Loads each batch in one transaction.
- Skips duplicate observations using a database unique constraint.
- Runs collection, saving, validation, transformation and loading
  through one pipeline command.
- Includes automated tests for collection and transformation.
- Includes an optional PostgreSQL rollback integration test.

## Tools

- Python 3.13
- Requests
- python-dotenv
- Psycopg 3
- PostgreSQL
- GraphQL
- JSON
- Python unittest
- Git and GitHub

## Project files

| File or folder | Purpose |
|---|---|
| `pipeline.py` | Collect, save, validate, transform and load one new snapshot |
| `main.py` | Fetch departures and save raw snapshots |
| `transform.py` | Validate and transform a saved snapshot |
| `load.py` | Validate and load a selected raw snapshot into PostgreSQL |
| `tests/test_main.py` | Test collection and retry behaviour |
| `tests/test_transform.py` | Test validation and transformation |
| `tests/test_load_integration.py` | Test database rollback after a failed batch |
| `sql/` | Database SQL files |
| `requirements.txt` | Required Python packages |
| `.env.example` | Example configuration without real credentials |
| `.env` | Private local configuration; ignored by Git |
| `data/raw/` | Collected API snapshots; ignored by Git |
| `data/processed/` | Output from the standalone transformation command; ignored by Git |
| `logs/` | Local operational logs; ignored by Git |

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

If the terminal already shows `(.venv)`, the environment is active.

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Configure credentials

For the first setup, copy the example configuration:

```powershell
Copy-Item .env.example .env
```

Register and subscribe through the
[Digitransit developer portal](https://portal-api.digitransit.fi/)
to obtain an API key.

Configure these values in `.env`, using your own credentials:

```dotenv
DIGITRANSIT_API_KEY=your_api_key

DB_HOST=localhost
DB_PORT=5432
DB_NAME=tampere_transport
DB_USER=transport_user
DB_PASSWORD=your_database_password
```

Keep actual credentials private. Never commit `.env` to GitHub.

Check that Git ignores it:

```powershell
git check-ignore .env
```

### 5. Prepare PostgreSQL

The current local setup uses:

- Database: `tampere_transport`
- Project database user: `transport_user`
- Table: `public.departure_observations`
- Unique constraint: `uq_departure_observation`

The database, user, table and constraint must already exist before
running the loader or pipeline. The Python scripts do not create them.

The project database user needs permission to insert into the table.

## Run the complete pipeline

```powershell
python pipeline.py
```

Each run:

1. Reads configuration from the environment and `.env`.
2. Requests departures from Digitransit.
3. Saves a new timestamped raw snapshot.
4. Reads the exact file saved during that run.
5. Validates and transforms the snapshot into flat records.
6. Loads the records into PostgreSQL in one transaction.
7. Logs the number of inserted rows and skipped duplicates.

The pipeline uses the path returned by the save function.
It does not search for the newest file in the raw data folder.

The snapshot filename is stored in the database as `source_file`,
linking observations to their raw source.

The pipeline passes transformed records directly to the database
loader. It does not write a separate processed JSON file.

Example successful log messages:

```text
Pipeline started
API attempt 1/3
API request succeeded
Raw snapshot saved to: ...
Validated and transformed 5 departures
Load committed: inserted=5, duplicates_skipped=0
Pipeline finished successfully
```

The API may return fewer than five departures.

### Verified pipeline run

On 23 October 2026, a complete pipeline run successfully:

- Collected and saved a new raw snapshot.
- Validated and transformed five departures.
- Committed five observations to PostgreSQL.
- Reported zero skipped duplicates.

## Run individual steps

The individual commands remain useful for learning,
inspection and retrying a saved snapshot.

### Collect departures only

```powershell
python main.py
```

This collects departures and saves a raw snapshot.
It does not load records into PostgreSQL.

Raw files are saved under:

```text
data/raw/
```

Example filename:

```text
departures_tampere_0835_20261023T161349_027220Z.json
```

Each snapshot contains:

- `metadata`: source, endpoint, stop ID, query and UTC collection times.
- `response`: the API response without transformations.

Each successful save creates a separate file.

The collector currently requests stop `tampere:0835`.
The endpoint and query are defined in `main.py`.

### Validate and transform a saved snapshot

```powershell
python transform.py data/raw/YOUR_SNAPSHOT_FILENAME.json
```

Replace `YOUR_SNAPSHOT_FILENAME.json` with an actual filename.

This command writes flat departure records under:

```text
data/processed/
```

The output uses the same filename as the raw snapshot.
Reprocessing the same snapshot replaces its processed output.

Validation completes before the processed output is written.
The raw snapshot remains unchanged.

### Load a saved snapshot into PostgreSQL

```powershell
python load.py data/raw/YOUR_SNAPSHOT_FILENAME.json
```

The loader reads the raw snapshot, validates and transforms it,
then loads its records in one transaction.

It does not require a processed JSON file.

This command can retry loading a saved snapshot after a database
problem has been fixed.

## Validation and transformed fields

Validation checks include:

- Required fields and expected data types.
- Matching stop IDs in metadata and the API response.
- A collection timestamp containing a timezone.
- Consistency between real-time departure and delay values.

Invalid data stops processing before database loading begins.

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

The loader also stores `source_file`, containing the raw snapshot
filename.

## Transactions and duplicates

A transaction groups the inserts into one database operation.

- If the complete batch succeeds, the transaction commits.
- If an insert fails, the transaction rolls back the entire batch.

The loader reports inserted and skipped counts after the transaction
has committed.

The unique constraint `uq_departure_observation` prevents duplicate
observations. The insert uses `ON CONFLICT ... DO NOTHING` to skip
conflicts with that constraint.

Loading the same unchanged snapshot again skips observations
already stored in the database.

A newly collected snapshot represents a new observation time.
It may contain trips seen in earlier snapshots.

## Reliability and logging

The collector makes up to three attempts for:

- Connection failures, except SSL certificate errors.
- Timeouts.
- HTTP 500, 502, 503 and 504 responses.

It waits 2 seconds before the second attempt and 4 seconds before
the third attempt.

Authentication errors, rate limits, invalid JSON and GraphQL errors
stop collection without retries.

Logs are written to the terminal and:

```text
logs/pipeline.log
```

Log timestamps use UTC.

- `INFO`: normal progress.
- `WARNING`: a temporary collection failure before a retry.
- `ERROR`: a failed run.

For `pipeline.py`, `main.py` and `load.py`:

- Exit code `0` means success.
- Exit code `1` means a handled failure.

Check the exit code immediately after running a command:

```powershell
$LASTEXITCODE
```

View recent logs:

```powershell
Get-Content .\logs\pipeline.log -Tail 15
```

If validation or database loading fails after a raw snapshot has
been saved, the raw file remains available for investigation
and reprocessing.

## Understanding the data

A route can have several patterns, representing different directions
or stop sequences. A trip is a specific journey.

Departure values are seconds from the service day's midnight.
Adding a departure value to `serviceDay` gives its Unix timestamp.

Departure seconds can exceed 86400 for journeys continuing
after midnight.

Real-time departure values are predictions. They do not confirm
when a vehicle actually departed.

When `realtime` is false, the transformation sets predicted departure
and live delay to `null`. A timetable-only delay of zero is not
evidence that a vehicle is on time.

Cancellation status is preserved in `realtime_state` when supplied.
It must be considered before interpreting departure predictions.

Collection timestamps describe when this program collected data.
They do not identify when the provider originally generated
a prediction.

## Run tests

Run the standard test suite:

```powershell
python -m unittest discover -s tests -v
```

Collection and transformation tests use simulated data and do not
require a real API key or network connection.

The database integration test is skipped unless `RUN_DB_TESTS`
is set to `1`.

The tests cover selected behaviours, including:

- Retrying temporary collection failures.
- Stopping after the attempt limit.
- Avoiding retries for authentication, rate-limit and GraphQL errors.
- Converting departures into structured records.
- Representing unavailable live values as null.
- Rejecting missing identifiers and inconsistent delays.
- Handling departure times after midnight.

### Run the PostgreSQL rollback integration test

This test requires the configured local PostgreSQL database.

```powershell
$env:RUN_DB_TESTS = "1"
python -m unittest discover -s tests -p "test_load_integration.py" -v
Remove-Item Env:RUN_DB_TESTS
```

The test deliberately makes the second record in a batch invalid.
It then checks through a separate connection that the first record
was not committed.

The rollback integration test has passed against the local database.

Passing tests cover these scenarios, not every possible failure.
The complete pipeline has also been verified through a manual run.

## What I am learning

- API authentication and HTTP requests
- GraphQL queries and JSON responses
- Public transport routes, patterns, stops and trips
- Environment variables and secret handling
- Retries, backoff and logging
- Raw snapshots and collection metadata
- Data validation and transformation
- UTC timestamps and missing values
- PostgreSQL and parameterized SQL
- Database transactions and rollback
- Duplicate prevention with unique constraints
- Connecting reusable functions into a pipeline
- Automated testing with mocks and database integration tests
- Git and project documentation

## AI assistance

I use ChatGPT and Codex as learning assistants for explanations,
code suggestions, debugging, tests and documentation.

I write and run the project step by step, review the suggestions
and use the results to develop my own understanding.

## Planned next steps

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
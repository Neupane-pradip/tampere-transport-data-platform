# Tampere Public Transport Data Platform

A local data engineering learning project using Tampere public
transport data from Digitransit.

I am building this project step by step to learn how to collect,
validate, transform, store and analyse data from a real API.

The starting point is departures from **Hervannan kampus A**
in Tampere, stop `tampere:0835`.

## Project status

The project implements a local ETL pipeline with PostgreSQL storage,
pipeline execution tracking, automated tests and manual SQL analysis
and monitoring.

Collection depends on the local computer, network connection and
PostgreSQL service being available.

Email notifications are not included in this version.

A written analysis report remains to be completed.

## Data flow

```text
Digitransit API
    |
    v
Timestamped raw JSON snapshot
    |
    v
Validation and transformation
    |
    v
PostgreSQL departure observations
```

The pipeline also records execution progress and outcomes in
`public.pipeline_runs`.

## Current functionality

- Requests the next five departures from the selected stop.
- Collects timetable information and available real-time predictions.
- Reads credentials from environment variables and a private `.env`.
- Retries selected temporary API failures.
- Writes operational logs with UTC timestamps.
- Saves successful responses as timestamped raw JSON snapshots.
- Validates and transforms snapshots into flat departure records.
- Loads observations into PostgreSQL in one transaction.
- Skips duplicates using a database unique constraint.
- Records pipeline stages, outcomes, filenames and row counts.
- Includes automated collection, transformation and pipeline tests.
- Includes an optional database rollback integration test.
- Provides SQL quality checks, analysis and monitoring queries.

## Tools

- Python
- Requests
- python-dotenv
- Psycopg 3
- PostgreSQL
- GraphQL
- JSON
- Python unittest
- Windows Task Scheduler
- Git and GitHub

## Project files

| File or folder | Purpose |
|---|---|
| `main.py` | Collect departures and save raw snapshots |
| `transform.py` | Validate and transform a saved raw snapshot |
| `load.py` | Validate and load a selected raw snapshot |
| `pipeline.py` | Run collection through database loading with execution tracking |
| `run_tracking.py` | Record pipeline execution progress and outcomes |
| `sql/001_create_departure_observations.sql` | Create the observations table and constraints |
| `sql/002_create_pipeline_runs.sql` | Create the execution-tracking table |
| `sql/data_quality_checks.sql` | Inspect stored data quality |
| `sql/departure_analysis.sql` | Analyse availability, statuses and predicted delays |
| `sql/collection_monitoring.sql` | Inspect loaded snapshots and collection gaps |
| `sql/run_monitoring.sql` | Inspect execution outcomes, freshness and unfinished runs |
| `tests/test_main.py` | Test collection and retries |
| `tests/test_transform.py` | Test validation and transformation |
| `tests/test_pipeline_failure.py` | Test simulated collection-failure handling |
| `tests/test_load_integration.py` | Test PostgreSQL batch rollback |
| `requirements.txt` | Required Python packages |
| `.env.example` | Configuration template without actual credentials |
| `.env` | Private local configuration; ignored by Git |
| `data/raw/` | Raw snapshots; ignored by Git |
| `data/processed/` | Standalone transformation output; ignored by Git |
| `logs/` | Local logs; ignored by Git |

## Setup

Run commands from the project root in PowerShell.

### 1. Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If the terminal already shows `(.venv)`, activation may already
be complete.

### 2. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 3. Configure credentials

For a new setup only:

```powershell
Copy-Item .env.example .env
```

Do not overwrite an existing working `.env`.

Configure the following values locally:

```dotenv
DIGITRANSIT_API_KEY=your_api_key
DB_HOST=localhost
DB_PORT=5432
DB_NAME=tampere_transport
DB_USER=transport_user
DB_PASSWORD=your_database_password
```

Obtain an API key through the
[Digitransit developer portal](https://portal-api.digitransit.fi/).

Never commit actual credentials.

Check that Git ignores the local configuration:

```powershell
git check-ignore .env
```

### 4. Prepare PostgreSQL

The project expects:

- A local PostgreSQL server.
- Database `tampere_transport`.
- Login role `transport_user` with the configured password.
- Permission for that role to connect and create project tables
  in the `public` schema.

Database and login-role creation are administrator setup steps.
They are not performed by the Python scripts.

For a fresh database, open pgAdmin Query Tool connected to
`tampere_transport`, then execute these files in order:

1. `sql/001_create_departure_observations.sql`
2. `sql/002_create_pipeline_runs.sql`

The scripts use `SET LOCAL ROLE transport_user`. Execute them as
that role, or as an administrator permitted to switch to it.

The scripts create tables and are intended for initial setup.
Do not rerun them against tables that already exist.

Existing installations with the observations table need only the
second script when adding run tracking.

## Run the complete pipeline

```powershell
python pipeline.py
```

Each execution:

1. Reads configuration.
2. Creates a pipeline run record.
3. Collects departures.
4. Saves a new raw snapshot.
5. Reads the exact file saved during that execution.
6. Validates and transforms its departures.
7. Loads observations in one transaction.
8. Records the outcome and committed row counts.

The pipeline does not search for the latest file.

It passes transformed records directly to the loader, without
writing a separate processed JSON file.

Check the exit code immediately after execution:

```powershell
$LASTEXITCODE
```

- `0`: successful execution and success tracking.
- `1`: a handled pipeline or tracking failure.

## Run individual steps

### Collect and save only

```powershell
python main.py
```

This saves a snapshot without loading PostgreSQL or creating a
pipeline run record.

### Validate and write processed JSON

```powershell
python transform.py data/raw/YOUR_SNAPSHOT_FILENAME.json
```

The output is written to `data/processed/` with the raw filename.

Reprocessing replaces that derived output. The raw file is unchanged.

### Load an existing raw snapshot

```powershell
python load.py data/raw/YOUR_SNAPSHOT_FILENAME.json
```

This validates, transforms and loads the selected raw file.
It does not require a processed file or create a pipeline run record.

It is useful for retrying a saved snapshot after a database issue.

## Raw snapshots

Raw snapshots are stored in `data/raw/`.

Example filename:

```text
departures_tampere_0835_20261023T161349_027220Z.json
```

Each file contains:

- `metadata`: source, endpoint, stop ID, query and UTC collection times.
- `response`: the API response.

The request-to-response interval includes retry attempts and waits.

Exclusive file creation prevents overwriting an existing snapshot.

## Stored observations

The table `public.departure_observations` stores:

| Field | Meaning |
|---|---|
| `observation_id` | Generated internal identifier |
| `observed_at_utc` | When collection received the response |
| `stop_id` | Stop identifier |
| `stop_name` | Stop name |
| `trip_id` | Journey identifier |
| `route_short_name` | Line number or label |
| `headsign` | Destination text, when available |
| `scheduled_departure_utc` | Timetable departure timestamp |
| `predicted_departure_utc` | Available predicted departure timestamp |
| `departure_delay_seconds` | Available predicted delay |
| `realtime` | Whether real-time information is available |
| `realtime_state` | Status supplied by the API |
| `source_file` | Raw snapshot filename |
| `loaded_at_utc` | Database loading timestamp |

Validation checks identifiers, types, stop consistency, timestamp
timezone information and delay consistency.

## Transactions and duplicates

`load_records()` inserts a complete batch in one transaction.

- Successful batches commit.
- An exception rolls back the batch.

Inserted and skipped counts are returned after commit.

The unique constraint `uq_departure_observation` uses:

- Stop ID.
- Trip ID.
- Scheduled departure timestamp.
- Observation timestamp.

Loading the same unchanged snapshot again skips stored observations.

The same trip can legitimately appear in later snapshots because
those rows represent observations at different collection times.

Database constraints also check real-time values and delay consistency.

## Pipeline run tracking

`public.pipeline_runs` stores:

- A UUID identifying the execution.
- Start and finish timestamps.
- Status: `running`, `succeeded` or `failed`.
- Execution stage.
- Raw snapshot filename, when available.
- Validated, inserted and duplicate counts, when known.
- Exception class for recorded failures.

A successful snapshot containing zero departures can still produce
a successful run record.

Run tracking uses separate transactions from departure loading.

If observations commit but success tracking fails, the observations
remain stored. The pipeline logs that distinction and returns `1`.

If PostgreSQL is unavailable before tracking starts, no run record
may be created. Inspect the logs in that situation.

An interrupted process can leave a run marked `running`.
That status requires investigation rather than assuming it is active.

Tracking began when this feature was introduced. Older executions
are not reconstructed automatically.

## Retries and logging

Collection makes up to three attempts for:

- Connection failures other than SSL certificate errors.
- Timeouts.
- HTTP 500, 502, 503 and 504 responses.

The retry waits are 2 seconds and then 4 seconds.

Authentication errors, rate limits, SSL certificate problems,
invalid JSON and GraphQL errors are not retried.

Logs appear in the terminal and:

```text
logs/pipeline.log
```

Log timestamps use UTC.

```powershell
Get-Content .\logs\pipeline.log -Tail 25
```

Saved raw files remain available if later validation or loading fails.

## SQL checks and analysis

Open pgAdmin Query Tool connected to `tampere_transport`.
Execute queries individually from these files.

### Data quality

`sql/data_quality_checks.sql` checks:

- Observation counts.
- Rows per snapshot.
- Selected missing or blank required fields.
- Real-time field consistency.
- Predicted delay calculations.
- Repeated observation identities.

The initial checks passed against ten observations from two snapshots.

Run the checks again as the dataset grows.

### Departure analysis

`sql/departure_analysis.sql` summarises:

- Real-time availability and its percentage.
- Status counts.
- Predicted delay averages and ranges.
- Early, exactly on-schedule and late predictions.
- Availability and predicted delays by route.
- Individual observations with the largest predicted delays.

Delay summaries exclude observations marked `CANCELED`.

### Monitoring

`sql/collection_monitoring.sql` inspects loaded observation times,
snapshots, daily counts and gaps.

`sql/run_monitoring.sql` inspects recorded execution outcomes,
empty successful runs, failures, freshness and long-running records.

Daily grouping uses Helsinki calendar dates.

These SQL files are manual tools. They are not automatically executed
by the pipeline and do not send notifications.

## Local scheduled collection

The documented local schedule uses Windows Task Scheduler
to launch `pipeline.py` every five minutes without overlapping runs.

To reproduce the task, create a task with:

- A daily trigger repeating every five minutes indefinitely.
- Program: the absolute path to `.venv\Scripts\python.exe`.
- Arguments: the quoted absolute path to `pipeline.py`.
- Start in: the project root directory.
- Existing-instance policy: do not start a new instance.
- Security option for the current setup: run only when the user is logged on.

Use paths for your own checkout.

The interval must fit the API subscription allowance.

Verify a scheduled execution through Task Scheduler history,
`logs/pipeline.log` and recent `pipeline_runs` rows.

Collection requires the computer to be awake, PostgreSQL to be
running and network access to be available.

This project is not hosted independently of the local computer.

## Tests

Run tests with database integration disabled:

```powershell
$env:RUN_DB_TESTS = "0"
python -m unittest discover -s tests -v
Remove-Item Env:RUN_DB_TESTS
```

These tests use simulated collection responses and mocked pipeline
dependencies. They do not require live API requests.

The database integration test is skipped by default.

To run the rollback test against the configured local database:

```powershell
$env:RUN_DB_TESTS = "1"
python -m unittest discover -s tests -p "test_load_integration.py" -v
Remove-Item Env:RUN_DB_TESTS
```

The integration test deliberately makes a batch invalid and checks
that no partial batch remains committed.

The rollback integration test previously passed against the local
database.

Tests cover selected scenarios, not every possible failure.
Run-tracking success and empty-response paths do not yet have
dedicated automated pipeline tests.

## Interpreting the data

Departure values are seconds from the service day's midnight.
Adding them to `serviceDay` gives a Unix timestamp.

Values above 86400 support services continuing after midnight.

Predictions do not confirm actual departure times.

For timetable-only rows, prediction and delay are `NULL`.
Zero is a predicted delay value, not a substitute for missing data.

A negative delay means an early prediction.
A positive delay means a late prediction.

Repeated observations of one trip contribute repeatedly to current
SQL summaries. Observation counts are not unique-departure counts.

The dataset covers one selected stop and collected time periods.
It does not represent the entire transport network.

## Remaining work for this version

- Verify scheduled collection over a documented period.
- Write an exploratory report with actual results and collection gaps.
- Re-run tests and SQL quality checks before the final checkpoint.

## Possible future improvements

- Automatic monitoring and notifications.
- Additional pipeline and run-tracking tests.
- Cloud deployment independent of the local computer.
- More stops and configurable collection settings.

## What I am learning

- HTTP APIs, authentication and GraphQL.
- Retries and operational logging.
- Raw data snapshots and provenance.
- Validation, transformation and UTC timestamps.
- PostgreSQL, parameterized SQL and constraints.
- Transactions, rollback and duplicate prevention.
- Pipeline execution tracking.
- Automated tests and mocks.
- SQL analysis and monitoring.
- Local scheduling.
- Git and project documentation.

## AI assistance

I use ChatGPT and Codex for explanations, code suggestions,
debugging, tests and documentation.

I write and run the project step by step, review suggestions
and use the results to develop my own understanding.

## Data source

This project uses the Digitransit Waltti Routing API.

- [Routing API documentation](https://digitransit.fi/en/developers/apis/1-routing-api/)
- [Developer portal](https://portal-api.digitransit.fi/)
- [Terms of use](https://digitransit.fi/en/developers/apis/7-terms-of-use/)

This is an independent learning project and is not an official
Nysse or Digitransit service.
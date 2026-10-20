# Tampere Public Transport Data Platform

A step-by-step data engineering project using Tampere public transport
data from Digitransit.

## Current functionality

- Requests the next five departures from Hervannan kampus A.
- Collects scheduled times and available real-time predictions.
- Checks for HTTP errors, GraphQL errors and missing stop data.
- Saves each successful response as a timestamped JSON snapshot.
- Records the endpoint, query and collection timestamps.
- Keeps API keys outside source code.

## Tools

- Python
- Requests
- GraphQL
- JSON
- Git

## Setup

Run these commands from the project folder.

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Copy the environment example:

```powershell
Copy-Item .env.example .env
```

Open `.env` and enter your Digitransit API key:

```dotenv
DIGITRANSIT_API_KEY=your_api_key
```

Get a key through the [Digitransit developer portal](https://portal-api.digitransit.fi/).

Never commit `.env` or share your key.

## Run

```powershell
python main.py
```

The program prints the API response and saves a snapshot under:

```text
data/raw/
```

Each snapshot contains:

- `metadata`: source, endpoint, stop ID, query and UTC collection times.
- `response`: the API response without transformations.

Generated snapshots are excluded from Git.

## Understanding the data

The starting stop is Hervannan kampus A, ID `tampere:0835`.

Departure times are expressed as seconds from the service day's midnight.
Adding a departure value to `serviceDay` gives its Unix timestamp.

Real-time departure values are predictions, not confirmed actual departures.

When `realtime` is false, a delay value of zero must not be interpreted
as evidence that the service is on time.

Collection timestamps show when this program requested and received data.
They do not show when the provider originally generated a prediction.

## What I am learning

- API authentication and HTTP requests
- GraphQL queries and JSON responses
- Routes, patterns, stops and trips
- Environment variables and secret handling
- Basic error checks
- Raw snapshots and collection metadata

## Planned next steps

- Retries and logging
- Data validation
- PostgreSQL loading
- SQL transformations
- Orchestration and monitoring
- Analysis of collected predictions

## Data source

[Digitransit Routing API documentation](https://digitransit.fi/en/developers/apis/1-routing-api/)
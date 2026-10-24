-- Tampere transport collection monitoring
--
-- These queries inspect loaded departure observations.
-- They do not record every pipeline attempt.
-- Successful snapshots containing zero departures do not
-- appear in this table.


-- Monitor 1: Check the latest loaded observation time.
SELECT
    MAX(observed_at_utc) AS latest_observed_at,
    CURRENT_TIMESTAMP AS checked_at,
    CURRENT_TIMESTAMP - MAX(observed_at_utc) AS time_since_latest
FROM public.departure_observations;


-- Monitor 2: Show recent loaded snapshots.
SELECT
    source_file,
    COUNT(*) AS observation_count,
    MIN(observed_at_utc) AS observed_at
FROM public.departure_observations
GROUP BY source_file
ORDER BY observed_at DESC
LIMIT 20;


-- Monitor 3: Summarize collection by Helsinki calendar date.
SELECT
    (
        observed_at_utc AT TIME ZONE 'Europe/Helsinki'
    )::date AS collection_date_helsinki,

    COUNT(DISTINCT source_file) AS loaded_snapshots,
    COUNT(*) AS total_observations,
    MIN(observed_at_utc) AS first_observed_at,
    MAX(observed_at_utc) AS last_observed_at
FROM public.departure_observations
GROUP BY
    (
        observed_at_utc AT TIME ZONE 'Europe/Helsinki'
    )::date
ORDER BY collection_date_helsinki DESC;


-- Monitor 4: Measure intervals between recent loaded snapshots.
WITH snapshots AS (
    SELECT
        source_file,
        MIN(observed_at_utc) AS observed_at
    FROM public.departure_observations
    GROUP BY source_file
),
snapshot_intervals AS (
    SELECT
        source_file,
        observed_at,

        LAG(observed_at) OVER (
            ORDER BY observed_at, source_file
        ) AS previous_observed_at
    FROM snapshots
)
SELECT
    source_file,
    previous_observed_at,
    observed_at,
    observed_at - previous_observed_at AS collection_interval
FROM snapshot_intervals
ORDER BY observed_at DESC, source_file DESC
LIMIT 20;


-- Monitor 5: Find gaps longer than ten minutes.
-- This is an investigation threshold for a five-minute schedule.
WITH snapshots AS (
    SELECT
        source_file,
        MIN(observed_at_utc) AS observed_at
    FROM public.departure_observations
    GROUP BY source_file
),
snapshot_intervals AS (
    SELECT
        source_file,
        observed_at,

        LAG(observed_at) OVER (
            ORDER BY observed_at, source_file
        ) AS previous_observed_at
    FROM snapshots
)
SELECT
    source_file,
    previous_observed_at,
    observed_at,
    observed_at - previous_observed_at AS collection_gap
FROM snapshot_intervals
WHERE observed_at - previous_observed_at > INTERVAL '10 minutes'
ORDER BY observed_at DESC, source_file DESC;
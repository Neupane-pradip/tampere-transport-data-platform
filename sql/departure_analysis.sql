-- Tampere public transport departure analysis
--
-- Each row represents an observation at collection time.
-- The same trip may appear in multiple snapshots.
-- Delays describe predictions, not confirmed actual departures.


-- Analysis 1: Count observations by real-time availability.
SELECT
    COUNT(*) AS total_observations,

    COUNT(*) FILTER (
        WHERE realtime = TRUE
    ) AS realtime_observations,

    COUNT(*) FILTER (
        WHERE realtime = FALSE
    ) AS timetable_only_observations
FROM public.departure_observations;


-- Analysis 2: Calculate real-time availability as a percentage.
SELECT
    COUNT(*) AS total_observations,

    COUNT(*) FILTER (
        WHERE realtime = TRUE
    ) AS realtime_observations,

    ROUND(
        100.0 * COUNT(*) FILTER (WHERE realtime = TRUE)
        / NULLIF(COUNT(*), 0),
        2
    ) AS realtime_percentage
FROM public.departure_observations;


-- Analysis 3: Count observations by status supplied by the API.
SELECT
    realtime_state,
    COUNT(*) AS observation_count
FROM public.departure_observations
GROUP BY realtime_state
ORDER BY observation_count DESC, realtime_state;


-- Analysis 4: Summarize predicted delays.
-- Exclude cancelled observations from delay summaries.
SELECT
    COUNT(*) AS observations_with_delay,
    ROUND(
        AVG(departure_delay_seconds),
        2
    ) AS average_delay_seconds,
    MIN(departure_delay_seconds) AS minimum_delay_seconds,
    MAX(departure_delay_seconds) AS maximum_delay_seconds
FROM public.departure_observations
WHERE realtime = TRUE
  AND departure_delay_seconds IS NOT NULL
  AND realtime_state <> 'CANCELED';


-- Analysis 5: Count early, exactly on-schedule and late predictions.
SELECT
    COUNT(*) FILTER (
        WHERE departure_delay_seconds < 0
    ) AS early_predictions,

    COUNT(*) FILTER (
        WHERE departure_delay_seconds = 0
    ) AS exactly_on_schedule_predictions,

    COUNT(*) FILTER (
        WHERE departure_delay_seconds > 0
    ) AS late_predictions
FROM public.departure_observations
WHERE realtime = TRUE
  AND departure_delay_seconds IS NOT NULL
  AND realtime_state <> 'CANCELED';


-- Analysis 6: Compare real-time availability by route.
SELECT
    route_short_name,
    COUNT(*) AS total_observations,

    COUNT(*) FILTER (
        WHERE realtime = TRUE
    ) AS realtime_observations,

    ROUND(
        100.0 * COUNT(*) FILTER (WHERE realtime = TRUE)
        / NULLIF(COUNT(*), 0),
        2
    ) AS realtime_percentage
FROM public.departure_observations
GROUP BY route_short_name
ORDER BY route_short_name;


-- Analysis 7: Summarize predicted delays by route.
SELECT
    route_short_name,
    COUNT(*) AS observations_with_delay,

    ROUND(
        AVG(departure_delay_seconds),
        2
    ) AS average_delay_seconds,

    MIN(departure_delay_seconds) AS minimum_delay_seconds,
    MAX(departure_delay_seconds) AS maximum_delay_seconds
FROM public.departure_observations
WHERE realtime = TRUE
  AND departure_delay_seconds IS NOT NULL
  AND realtime_state <> 'CANCELED'
GROUP BY route_short_name
ORDER BY route_short_name;


-- Analysis 8: Inspect the ten largest predicted delays.
SELECT
    observed_at_utc,
    route_short_name,
    headsign,
    trip_id,
    scheduled_departure_utc,
    predicted_departure_utc,
    departure_delay_seconds,
    realtime_state,
    source_file
FROM public.departure_observations
WHERE realtime = TRUE
  AND departure_delay_seconds IS NOT NULL
  AND realtime_state <> 'CANCELED'
ORDER BY
    departure_delay_seconds DESC,
    observed_at_utc DESC,
    trip_id,
    scheduled_departure_utc,
    stop_id
LIMIT 10;
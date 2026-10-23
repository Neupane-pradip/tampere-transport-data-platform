-- Check 1: Count all stored departure observations.
SELECT COUNT(*) AS total_observations
FROM public.departure_observations;


-- Check 2: Summarize observations from each raw snapshot.
SELECT
    source_file,
    COUNT(*) AS observation_count,
    MIN(observed_at_utc) AS first_observed_at,
    MAX(observed_at_utc) AS last_observed_at
FROM public.departure_observations
GROUP BY source_file
ORDER BY first_observed_at DESC;

-- Check 3: Count missing required values.
SELECT
    COUNT(*) FILTER (
        WHERE observed_at_utc IS NULL
    ) AS missing_observed_at,

    COUNT(*) FILTER (
        WHERE stop_id IS NULL OR TRIM(stop_id) = ''
    ) AS missing_stop_id,

    COUNT(*) FILTER (
        WHERE trip_id IS NULL OR TRIM(trip_id) = ''
    ) AS missing_trip_id,

    COUNT(*) FILTER (
        WHERE scheduled_departure_utc IS NULL
    ) AS missing_scheduled_departure,

    COUNT(*) FILTER (
        WHERE source_file IS NULL OR TRIM(source_file) = ''
    ) AS missing_source_file
FROM public.departure_observations;

-- Check 4: Find inconsistent real-time values.
SELECT
    COUNT(*) FILTER (
        WHERE realtime IS NULL
    ) AS missing_realtime_flag,

    COUNT(*) FILTER (
        WHERE realtime = TRUE
          AND (
              predicted_departure_utc IS NULL
              OR departure_delay_seconds IS NULL
          )
    ) AS realtime_missing_prediction,

    COUNT(*) FILTER (
        WHERE realtime = FALSE
          AND (
              predicted_departure_utc IS NOT NULL
              OR departure_delay_seconds IS NOT NULL
          )
    ) AS timetable_only_with_live_values
FROM public.departure_observations;

-- Check 5: Find delays that disagree with departure timestamps.
SELECT
    source_file,
    trip_id,
    scheduled_departure_utc,
    predicted_departure_utc,
    departure_delay_seconds,
    EXTRACT(
        EPOCH FROM (
            predicted_departure_utc - scheduled_departure_utc
        )
    ) AS calculated_delay_seconds
FROM public.departure_observations
WHERE realtime = TRUE
  AND departure_delay_seconds <> EXTRACT(
      EPOCH FROM (
          predicted_departure_utc - scheduled_departure_utc
      )
  );

-- Check 6: Find repeated observations for the same trip,
-- stop, scheduled departure and collection time.
SELECT
    observed_at_utc,
    stop_id,
    trip_id,
    scheduled_departure_utc,
    COUNT(*) AS observation_count
FROM public.departure_observations
GROUP BY
    observed_at_utc,
    stop_id,
    trip_id,
    scheduled_departure_utc
HAVING COUNT(*) > 1;
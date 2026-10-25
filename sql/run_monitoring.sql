-- Pipeline execution monitoring
--
-- Run tracking began when pipeline_runs was introduced.
-- Older executions are not reconstructed automatically.
--
-- These queries are manual checks. They do not send alerts.


-- Check 1: Show recent executions.
SELECT
    run_id,
    started_at_utc,
    finished_at_utc,
    finished_at_utc - started_at_utc AS duration,
    status,
    stage,
    source_file,
    records_validated,
    records_inserted,
    duplicates_skipped,
    error_type
FROM public.pipeline_runs
ORDER BY started_at_utc DESC
LIMIT 20;


-- Check 2: Summarize executions by Helsinki start date.
SELECT
    (
        started_at_utc AT TIME ZONE 'Europe/Helsinki'
    )::date AS run_date_helsinki,

    COUNT(*) AS total_runs,

    COUNT(*) FILTER (
        WHERE status = 'succeeded'
    ) AS succeeded_runs,

    COUNT(*) FILTER (
        WHERE status = 'failed'
    ) AS failed_runs,

    COUNT(*) FILTER (
        WHERE status = 'running'
    ) AS running_runs,

    COUNT(*) FILTER (
        WHERE status = 'succeeded'
          AND records_validated = 0
    ) AS successful_empty_runs
FROM public.pipeline_runs
GROUP BY
    (
        started_at_utc AT TIME ZONE 'Europe/Helsinki'
    )::date
ORDER BY run_date_helsinki DESC;


-- Check 3: Find recent recorded failures.
SELECT
    run_id,
    started_at_utc,
    finished_at_utc,
    stage,
    source_file,
    error_type
FROM public.pipeline_runs
WHERE status = 'failed'
ORDER BY started_at_utc DESC
LIMIT 20;


-- Check 4: Find runs marked running for longer than ten minutes.
-- These require investigation, not automatic status changes.
SELECT
    run_id,
    started_at_utc,
    stage,
    source_file,
    CURRENT_TIMESTAMP - started_at_utc AS time_since_start
FROM public.pipeline_runs
WHERE status = 'running'
  AND started_at_utc <
      CURRENT_TIMESTAMP - INTERVAL '10 minutes'
ORDER BY started_at_utc;


-- Check 5: Check execution and successful-run freshness.
SELECT
    MAX(started_at_utc) AS latest_recorded_start,

    MAX(finished_at_utc) FILTER (
        WHERE status = 'succeeded'
    ) AS latest_successful_finish,

    CURRENT_TIMESTAMP - MAX(started_at_utc)
        AS time_since_latest_start,

    CURRENT_TIMESTAMP - MAX(finished_at_utc) FILTER (
        WHERE status = 'succeeded'
    ) AS time_since_latest_success
FROM public.pipeline_runs;
import psycopg


def start_run(run_id, started_at, database_settings):
    """Record a new pipeline execution."""

    with psycopg.connect(**database_settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO public.pipeline_runs (
                    run_id,
                    started_at_utc,
                    status,
                    stage
                )
                VALUES (%s, %s, 'running', 'configuration')
                """,
                (run_id, started_at),
            )


def update_run_stage(
    run_id,
    stage,
    database_settings,
    source_file=None,
):
    """Record progress while the pipeline is running."""

    with psycopg.connect(**database_settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE public.pipeline_runs
                SET
                    stage = %s,
                    source_file = COALESCE(%s, source_file)
                WHERE run_id = %s
                  AND status = 'running'
                """,
                (stage, source_file, run_id),
            )

            if cursor.rowcount != 1:
                raise RuntimeError(
                    "Expected one running pipeline record to update."
                )


def finish_run(
    run_id,
    finished_at,
    status,
    stage,
    database_settings,
    records_validated=None,
    records_inserted=None,
    duplicates_skipped=None,
    error_type=None,
):
    """Record the final outcome of a pipeline execution."""

    with psycopg.connect(**database_settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE public.pipeline_runs
                SET
                    finished_at_utc = %s,
                    status = %s,
                    stage = %s,
                    records_validated = %s,
                    records_inserted = %s,
                    duplicates_skipped = %s,
                    error_type = %s
                WHERE run_id = %s
                  AND status = 'running'
                """,
                (
                    finished_at,
                    status,
                    stage,
                    records_validated,
                    records_inserted,
                    duplicates_skipped,
                    error_type,
                    run_id,
                ),
            )

            if cursor.rowcount != 1:
                raise RuntimeError(
                    "Expected one running pipeline record to finish."
                )
-- Run this file while connected to the tampere_transport database.
-- Run as transport_user, or as an administrator using SET ROLE.

BEGIN;

-- Create the table as the project user.
SET LOCAL ROLE transport_user;

CREATE TABLE public.departure_observations (
    -- PostgreSQL generates an internal ID for each observation.
    observation_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- When our pipeline received this prediction.
    observed_at_utc TIMESTAMPTZ NOT NULL,

    -- Stop and journey identifiers from Digitransit.
    stop_id TEXT NOT NULL,
    stop_name TEXT NOT NULL,
    trip_id TEXT NOT NULL,
    route_short_name TEXT NOT NULL,

    -- Destination text can be unavailable.
    headsign TEXT,

    -- Timetable departure and available live prediction.
    scheduled_departure_utc TIMESTAMPTZ NOT NULL,
    predicted_departure_utc TIMESTAMPTZ,
    departure_delay_seconds INTEGER,

    -- Preserve whether live information exists and its status.
    realtime BOOLEAN NOT NULL,
    realtime_state TEXT NOT NULL,

    -- Record which raw snapshot produced this observation.
    source_file TEXT NOT NULL,

    -- When the observation was loaded into PostgreSQL.
    loaded_at_utc TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Prevent reloading the same observation as another row.
    CONSTRAINT uq_departure_observation UNIQUE (
        stop_id,
        trip_id,
        scheduled_departure_utc,
        observed_at_utc
    ),

    -- Live values must agree with the availability flag.
    CONSTRAINT chk_realtime_values CHECK (
        (
            realtime = TRUE
            AND predicted_departure_utc IS NOT NULL
            AND departure_delay_seconds IS NOT NULL
        )
        OR
        (
            realtime = FALSE
            AND predicted_departure_utc IS NULL
            AND departure_delay_seconds IS NULL
        )
    ),

    -- A live delay must equal predicted time minus scheduled time.
    CONSTRAINT chk_departure_delay CHECK (
        realtime = FALSE
        OR predicted_departure_utc =
            scheduled_departure_utc
            + departure_delay_seconds * INTERVAL '1 second'
    )
);

-- Help queries that select a stop and an observation time range.
CREATE INDEX idx_departure_observations_stop_time
    ON public.departure_observations (
        stop_id,
        observed_at_utc
    );

COMMIT;
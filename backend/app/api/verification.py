
"""Calculate event confidence from available source evidence."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from backend.app.database import engine

router = APIRouter(prefix="/verify", tags=["Verification"])


@router.post("")
def verify_event(event_id: int):
    # Fetch the event timestamp and its stored geographic coordinates.
    event_query = text("""
        SELECT
            e.event_id,
            e.event_timestamp,
            l.latitude AS event_latitude,
            l.longitude AS event_longitude
        FROM events e
        LEFT JOIN LATERAL (
            SELECT latitude, longitude
            FROM locations
            WHERE event_id = e.event_id
            ORDER BY location_id
            LIMIT 1
        ) l ON TRUE
        WHERE e.event_id = :event_id
    """)

    # Retrieve all source evidence attached to this event.
    source_query = text("""
        SELECT
            source_type,
            source_timestamp,
            latitude,
            longitude,
            credibility_score
        FROM sources
        WHERE event_id = :event_id
    """)

    with engine.begin() as connection:
        event = connection.execute(
            event_query, {"event_id": event_id}
        ).mappings().first()

        if not event:
            raise HTTPException(
                status_code=404, detail="Event not found"
            )

        sources = connection.execute(
            source_query, {"event_id": event_id}
        ).mappings().all()

        # Use only source timestamps that can be compared with the event.
        temporal_scores = []
        for source in sources:
            timestamp = source["source_timestamp"]

            if timestamp is not None and event["event_timestamp"] is not None:
                # A difference of one hour gives a score of 0.5.
                hours_apart = abs(
                    (timestamp - event["event_timestamp"]).total_seconds()
                ) / 3600

                temporal_scores.append(1 / (1 + hours_apart))

        # Missing timestamps provide no temporal evidence.
        temporal_score = (
            sum(temporal_scores) / len(temporal_scores)
            if temporal_scores else 0.0
        )

        # Compare source coordinates with the event's stored location.
        spatial_scores = []
        event_lat = event["event_latitude"]
        event_lon = event["event_longitude"]

        if event_lat is not None and event_lon is not None:
            for source in sources:
                lat = source["latitude"]
                lon = source["longitude"]

                if lat is None or lon is None:
                    continue

                # ST_Distance on geography returns metres.
                distance_query = text("""
                    SELECT ST_Distance(
                        ST_SetSRID(
                            ST_MakePoint(:event_lon, :event_lat), 4326
                        )::geography,
                        ST_SetSRID(
                            ST_MakePoint(:source_lon, :source_lat), 4326
                        )::geography
                    )
                """)

                distance_m = connection.execute(
                    distance_query,
                    {
                        "event_lon": event_lon,
                        "event_lat": event_lat,
                        "source_lon": lon,
                        "source_lat": lat,
                    },
                ).scalar_one()

                # Nearby coordinates provide stronger spatial consistency.
                spatial_scores.append(
                    max(0.0, 1 - distance_m / 100_000)
                )

        spatial_score = (
            sum(spatial_scores) / len(spatial_scores)
            if spatial_scores else 0.0
        )

        # Use recorded credibility values; never invent missing scores.
        credibility_values = [
            float(source["credibility_score"])
            for source in sources
            if source["credibility_score"] is not None
        ]

        source_score = (
            sum(credibility_values) / len(credibility_values)
            if credibility_values else 0.0
        )

        # Multiple rows of the same type do not count as independent types.
        distinct_types = {
            source["source_type"]
            for source in sources
            if source["source_type"]
            and source["source_type"].lower() != "mock"
        }

        corroboration_score = min(len(distinct_types) / 3, 1.0)

        # Preserve the project's existing weighting.
        final_score = (
            temporal_score * 0.25
            + spatial_score * 0.25
            + source_score * 0.20
            + corroboration_score * 0.30
        )

        # These are heuristic statuses, not proof of truth.
        if final_score >= 0.85:
            status = "verified"
        elif final_score >= 0.60:
            status = "probable"
        else:
            status = "needs_review"

        # Save or refresh the current assessment for this event.
        connection.execute(
            text("""
                INSERT INTO verification (
                    event_id, temporal_score, spatial_score,
                    source_score, corroboration_score,
                    final_score, status, evidence_summary
                )
                VALUES (
                    :event_id, :temporal_score, :spatial_score,
                    :source_score, :corroboration_score,
                    :final_score, :status,
                    CAST(:evidence_summary AS JSONB)
                )
                ON CONFLICT (event_id)
                DO UPDATE SET
                    temporal_score = EXCLUDED.temporal_score,
                    spatial_score = EXCLUDED.spatial_score,
                    source_score = EXCLUDED.source_score,
                    corroboration_score = EXCLUDED.corroboration_score,
                    final_score = EXCLUDED.final_score,
                    status = EXCLUDED.status,
                    evidence_summary = EXCLUDED.evidence_summary,
                    verified_at = CURRENT_TIMESTAMP
            """),
            {
                "event_id": event_id,
                "temporal_score": temporal_score,
                "spatial_score": spatial_score,
                "source_score": source_score,
                "corroboration_score": corroboration_score,
                "final_score": final_score,
                "status": status,
                "evidence_summary": (
                    '{"source_count": ' + str(len(sources))
                    + ', "timestamp_samples": ' + str(len(temporal_scores))
                    + ', "spatial_samples": ' + str(len(spatial_scores))
                    + ', "credible_source_samples": '
                    + str(len(credibility_values))
                    + ', "independent_source_types": '
                    + str(len(distinct_types)) + '}'
                ),
            },
        )

        # Keep the event's summary fields synchronized with verification.
        connection.execute(
            text("""
                UPDATE events
                SET credibility_score = :score,
                    verification_status = :status
                WHERE event_id = :event_id
            """),
            {
                "score": final_score,
                "status": status,
                "event_id": event_id,
            },
        )

    return {
        "event_id": event_id,
        "status": status,
        "confidence": round(final_score, 4),
        "evidence": {
            "temporal_score": round(temporal_score, 4),
            "spatial_score": round(spatial_score, 4),
            "source_score": round(source_score, 4),
            "corroboration_score": round(corroboration_score, 4),
        },
    }

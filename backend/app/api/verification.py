"""Calculate event confidence from source evidence and persist its status."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from backend.app.database import engine

router = APIRouter(
    prefix="/verify",
    tags=["Verification"]
)


@router.post("")
def verify_event(event_id: int):
    # Recalculate confidence from the evidence currently attached to the event.

    source_query = text("""
        SELECT
            COUNT(*) AS source_count,
            COUNT(DISTINCT source_type) AS source_types
        FROM sources
        WHERE event_id = :event_id
    """)

    event_query = text("""
        SELECT event_id
        FROM events
        WHERE event_id = :event_id
    """)

    # Keep the verification record and event status synchronized in one transaction.
    with engine.begin() as connection:

        event = connection.execute(
            event_query,
            {"event_id": event_id}
        ).first()

        if not event:
            raise HTTPException(
                status_code=404,
                detail="Event not found"
            )

        source_info = connection.execute(
            source_query,
            {"event_id": event_id}
        ).mappings().first()

        source_count = source_info["source_count"]
        source_types = source_info["source_types"]

        # Cap evidence contributions at 1.0 so extra sources cannot inflate scores.
        source_score = min(source_types / 3, 1.0)
        corroboration_score = min(source_count / 3, 1.0)

        temporal_score = 0.5
        spatial_score = 0.5

        final_score = (
            temporal_score * 0.25
            + spatial_score * 0.25
            + source_score * 0.20
            + corroboration_score * 0.30
        )

        # Convert the weighted score into the status consumed by the API clients.
        if final_score >= 0.85:
            status = "verified"
        elif final_score >= 0.60:
            status = "probable"
        else:
            status = "needs_review"

        # Upsert so repeated verification refreshes the existing assessment.
        connection.execute(
            text("""
                INSERT INTO verification (
                    event_id,
                    temporal_score,
                    spatial_score,
                    source_score,
                    corroboration_score,
                    final_score,
                    status,
                    evidence_summary
                )
                VALUES (
                    :event_id,
                    :temporal_score,
                    :spatial_score,
                    :source_score,
                    :corroboration_score,
                    :final_score,
                    :status,
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
                    '{"source_count": '
                    + str(source_count)
                    + ', "source_types": '
                    + str(source_types)
                    + '}'
                )
            }
        )

        # Mirror the result on events for fast filtering and list responses.
        connection.execute(
            text("""
                UPDATE events
                SET
                    credibility_score = :score,
                    verification_status = :status
                WHERE event_id = :event_id
            """),
            {
                "score": final_score,
                "status": status,
                "event_id": event_id
            }
        )

    return {
        "event_id": event_id,
        "status": status,
        "confidence": round(final_score, 4)
    }
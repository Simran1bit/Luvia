from datetime import datetime

from pydantic import BaseModel


class EventCreate(BaseModel):
    event_type: str
    title: str
    description: str | None = None

    event_timestamp: datetime

    latitude: float
    longitude: float

    city: str | None = None
    state: str | None = None

    severity: str = "unknown"

    source: str = "MOCK"
    source_name: str | None = None
    source_url: str | None = None
"""Configure the FastAPI application and register its API routes."""

import os  # let us interact with env variables

from dotenv import load_dotenv
from fastapi import FastAPI
from sqlalchemy import create_engine, text

from backend.app.api.analytics import router as analytics_router
from backend.app.api.events import router as events_router
from backend.app.api.map import router as map_router
from backend.app.api.verification import router as verification_router

# Load local environment values before creating the database engine.
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Share one pooled engine so every route reuses managed database connections.
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True #checks Is this connection still alive? if not create a new one
)

app = FastAPI(
    title="LLUVIA API",
    description="AI-powered Weather Intelligence, Verification & Analytics",
    version="0.1.0"
)

# Keep each feature's endpoints in its own router for clearer API ownership.
# Add all the endpoints defined by the Events router to this FastAPI application
app.include_router(events_router)
app.include_router(analytics_router)
app.include_router(map_router)
app.include_router(verification_router)

@app.get("/") #Decorator
# Provide a lightweight endpoint for confirming that the API is running.
def root():
    return {
        "project": "LLUVIA",
        "status": "running"
    }


@app.get("/health/db")
def database_health():
    # Use a simple query to verify both connectivity and query execution.
    with engine.connect() as connection: #with: connection will be closed automatically after the block
        result = connection.execute(text("SELECT 1"))
        return {
            "database": "connected",
            "result": result.scalar()
        }
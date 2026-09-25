"""Create the shared SQLAlchemy engine from the configured database URL."""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine

# Read the database setting from the local environment or deployment config.
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Fail during startup instead of allowing a later, harder-to-diagnose error.
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

# if DATABASE_URL.startswith("postgresql://"):
#     DATABASE_URL = DATABASE_URL.replace(
#         "postgresql://",
#         "postgresql+psycopg://",
#         1
#     )

# Enable connection health checks before pooled connections are reused.
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)
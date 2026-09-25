import os #let us interact with env variables

from dotenv import load_dotenv
from fastapi import FastAPI
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgresql://",
        "postgresql+psycopg://",
        1
    )

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True #checks Is this connection still alive? if not create a new one
)

app = FastAPI(title="LLUVIA API")


@app.get("/") #Decorator
# when someone sends a GET request to /, excute the function root()
def root():
    return {
        "project": "LLUVIA",
        "status": "running"
    }


@app.get("/health/db")
def database_health():
    with engine.connect() as connection: #with: connection will be closed automatically after the block
        result = connection.execute(text("SELECT 1"))
        return {
            "database": "connected",
            "result": result.scalar()
        }
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Default to SQLite when no DATABASE_URL is set (no Docker/Postgres needed).
# Set DATABASE_URL=postgresql://... in the environment to use Postgres instead.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./dfr.db"
)

# SQLite needs check_same_thread=False for FastAPI's async request handling
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

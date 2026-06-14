"""SQLAlchemy engine and session factory."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import DATABASE_URL

engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_session() -> Session:
    """Get a new database session."""
    return SessionLocal()


def init_database():
    """Create all tables in the database."""
    from src.storage.models import Base
    Base.metadata.create_all(bind=engine)
    print(f"Database initialized at: {DATABASE_URL}")

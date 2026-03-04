"""
Database connection management.

Usage
-----
from data.db import get_db, init_db

init_db()                        # call once at startup

with get_db() as session:
    session.add(some_object)
    session.commit()
"""

from contextlib import contextmanager
from pathlib import Path

from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sqlite3
import shutil
from datetime import datetime
import os

from data.models import Base

# ---------------------------------------------------------------------------
# Engine — points to the SQLite file inside the data/ directory
# ---------------------------------------------------------------------------

_DB_PATH = Path(__file__).parent / "nse_fundamentals.db"
_ENGINE_URL = f"sqlite:///{_DB_PATH}"

engine = create_engine(
    _ENGINE_URL,
    connect_args={"check_same_thread": False},  # safe for single-threaded use
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def init_db() -> None:
    """Create all tables if they do not already exist."""
    logger.info(f"Initialising database at {_DB_PATH}")

    # If the DB file exists but is not a valid SQLite database, back it up
    # and remove it so SQLAlchemy can create a fresh one.
    if _DB_PATH.exists():
        try:
            conn = sqlite3.connect(str(_DB_PATH))
            # simple pragma to validate DB; will raise if file is invalid
            conn.execute("PRAGMA schema_version;")
            conn.close()
        except sqlite3.DatabaseError as exc:
            logger.warning(
                "Detected invalid SQLite DB file at {} — backing up and recreating."
                .format(_DB_PATH)
            )
            timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
            backup_name = f"{_DB_PATH.stem}.corrupt.{timestamp}.bak"
            backup_path = _DB_PATH.with_name(backup_name)
            try:
                shutil.move(str(_DB_PATH), str(backup_path))
                logger.info(f"Backed up corrupt DB to {backup_path}")
            except Exception:
                # if move fails, attempt to remove the file as a last resort
                try:
                    os.remove(_DB_PATH)
                    logger.info("Removed corrupt DB file")
                except Exception:
                    logger.error("Failed to backup or remove corrupt DB file")
                    raise

    Base.metadata.create_all(bind=engine)
    logger.success("Database initialised — all tables ready.")


@contextmanager
def get_db():
    """
    Yield a SQLAlchemy session and guarantee it is closed on exit.

    Example
    -------
    with get_db() as session:
        results = session.query(Company).all()
    """
    session = SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
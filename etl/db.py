"""SQLAlchemy engine construction from environment variables."""
import logging
import os

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

log = logging.getLogger(__name__)

_REQUIRED = ("DB_ENGINE", "DB_USER", "DB_PASSWORD", "DB_NAME")


def get_db_engine() -> Engine:
    """Build a SQLAlchemy engine from DB_* env vars."""
    missing = [k for k in _REQUIRED if not os.getenv(k)]
    if missing:
        log.error("Missing required env vars: %s", ", ".join(missing))
        raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")

    engine = os.getenv("DB_ENGINE")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    name = os.getenv("DB_NAME")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")

    url = f"{engine}://{user}:{password}@{host}:{port}/{name}"
    return create_engine(url)

"""Top-level pipeline entrypoint: STG (Python) -> Core SQL -> Marts SQL."""
import logging
import time
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Engine

from etl.config import LOG_LEVEL
from etl.db import get_db_engine
from etl.run_stg import run_stg

log = logging.getLogger(__name__)


def run_sql_dir(engine: Engine, dir_path: str) -> None:
    """Execute every *.sql file in dir_path in alphabetical order."""
    d = Path(dir_path)
    if not d.is_dir():
        log.warning("SQL dir does not exist, skipping: %s", dir_path)
        return

    files = sorted(d.glob("*.sql"))
    for f in files:
        start = time.perf_counter()
        log.info("SQL  %s", f)
        sql = f.read_text()
        try:
            with engine.begin() as conn:
                conn.execute(text(sql))
        except Exception:
            log.exception("SQL failed: %s", f)
            raise
        log.info("DONE %s in %.2fs", f.name, time.perf_counter() - start)


def main() -> None:
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    engine = get_db_engine()
    run_stg(engine)
    run_sql_dir(engine, "sql/core")
    run_sql_dir(engine, "sql/marts")
    log.info("Pipeline completed successfully.")


if __name__ == "__main__":
    main()

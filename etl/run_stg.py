"""Orchestrate the STG stage: extract -> transform -> load for each source."""
import logging
import time

from sqlalchemy import text
from sqlalchemy.engine import Engine

from etl.config import LOG_LEVEL, SOURCES, STG_SCHEMA
from etl.db import get_db_engine
from etl.extract import read_xlsx
from etl.load import load_stg
from etl.transform import add_audit_cols, drop_empty_rows, normalize_columns

log = logging.getLogger(__name__)


def run_stg(engine: Engine) -> None:
    """Run STG for every entry in SOURCES; collect failures and re-raise at end."""
    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {STG_SCHEMA}"))

    failures: list[tuple[str, str, Exception]] = []

    for path, sheet, table in SOURCES:
        start = time.perf_counter()
        log.info("START %s [%s] -> %s", path, sheet, table)
        try:
            df = read_xlsx(path, sheet)
            df = normalize_columns(df)
            df = drop_empty_rows(df)
            df = add_audit_cols(df, path)
            load_stg(df, table, engine)
            log.info("DONE  %s -> %s in %.2fs", sheet, table, time.perf_counter() - start)
        except Exception as e:
            log.exception("FAIL  %s [%s] -> %s", path, sheet, table)
            failures.append((path, sheet, e))

    if failures:
        raise RuntimeError(f"STG stage completed with {len(failures)} failure(s)")


if __name__ == "__main__":
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    run_stg(get_db_engine())

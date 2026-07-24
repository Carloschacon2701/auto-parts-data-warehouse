"""Write a DataFrame to a staging table."""
import logging

import pandas as pd
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from etl.config import CHUNK_SIZE, STG_SCHEMA

log = logging.getLogger(__name__)


def load_stg(df: pd.DataFrame, table: str, engine: Engine, schema: str = STG_SCHEMA) -> None:
    """Replace a staging table with the contents of df."""
    log.info("Loading %d rows -> %s.%s", len(df), schema, table)
    try:
        df.to_sql(
            name=table,
            con=engine,
            schema=schema,
            if_exists="replace",
            index=False,
            chunksize=CHUNK_SIZE,
            method="multi",
        )
    except SQLAlchemyError:
        log.exception("Failed loading %s.%s", schema, table)
        raise
    log.info("Loaded %s.%s (%d rows)", schema, table, len(df))

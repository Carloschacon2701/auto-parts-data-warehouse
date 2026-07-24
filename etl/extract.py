"""Read a single Excel sheet into a DataFrame."""
import logging
import os

import pandas as pd

log = logging.getLogger(__name__)


def read_xlsx(path: str, sheet: str) -> pd.DataFrame:
    """Read one sheet from an .xlsx file."""
    if not os.path.exists(path):
        log.error("Excel file not found: %s", path)
        raise FileNotFoundError(path)

    df = pd.read_excel(path, sheet_name=sheet, engine="openpyxl")
    log.info("Extracted %d rows from %s [%s]", len(df), path, sheet)
    return df

"""Mechanical, source-agnostic cleaning for every DataFrame before staging."""
import os

import pandas as pd


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Lowercase, strip, and underscore-space column names (idempotent)."""
    df = df.copy()
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    return df


def drop_empty_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Drop rows where every value is NaN."""
    return df.dropna(how="all")


def add_audit_cols(df: pd.DataFrame, source_file: str) -> pd.DataFrame:
    """Add etl_loaded_at and etl_source_file audit columns."""
    df = df.copy()
    df["etl_loaded_at"] = pd.Timestamp.now()
    df["etl_source_file"] = os.path.basename(source_file)
    return df


def to_datetime_safe(series: pd.Series) -> pd.Series:
    """Coerce to datetime; bad values become NaT."""
    return pd.to_datetime(series, errors="coerce")


def to_numeric_safe(series: pd.Series) -> pd.Series:
    """Coerce to numeric; bad values become NaN."""
    return pd.to_numeric(series, errors="coerce")

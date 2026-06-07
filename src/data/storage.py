from __future__ import annotations

from pathlib import Path

import pandas as pd


RAW_DATA_DIR = Path("data/raw")
PROCESSED_DATA_DIR = Path("data/processed")


def raw_index_path(index_id: str) -> Path:
    return RAW_DATA_DIR / f"{index_id}.csv"


def save_raw_index_data(index_id: str, df: pd.DataFrame) -> Path:
    path = raw_index_path(index_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return path


def load_raw_index_data(index_id: str) -> pd.DataFrame:
    return pd.read_csv(raw_index_path(index_id), parse_dates=["date"])

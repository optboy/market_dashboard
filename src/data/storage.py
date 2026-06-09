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


def append_raw_index_data(index_id: str, new_df: pd.DataFrame) -> tuple[Path, int]:
    path = raw_index_path(index_id)
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        existing = pd.read_csv(path, parse_dates=["date"])
        before_count = len(existing)
        combined = pd.concat([existing, new_df], ignore_index=True)
    else:
        before_count = 0
        combined = new_df.copy()

    combined["date"] = pd.to_datetime(combined["date"])
    combined = (
        combined.sort_values("date")
        .drop_duplicates(subset=["date"], keep="last")
        .reset_index(drop=True)
    )
    combined.to_csv(path, index=False)
    return path, max(0, len(combined) - before_count)


def load_raw_index_data(index_id: str) -> pd.DataFrame:
    return pd.read_csv(raw_index_path(index_id), parse_dates=["date"])

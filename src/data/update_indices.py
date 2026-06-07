from __future__ import annotations

from datetime import date, timedelta

from src.data.downloaders import fetch_index_ohlcv
from src.data.index_config import load_indices
from src.data.storage import save_raw_index_data


DEFAULT_LOOKBACK_DAYS = 365 * 2


def update_raw_index_data(
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[str]:
    """Download and save raw OHLCV data for all configured indices."""
    actual_end = end_date or date.today()
    actual_start = start_date or actual_end - timedelta(days=DEFAULT_LOOKBACK_DAYS)

    saved_paths: list[str] = []
    for index in load_indices():
        df = fetch_index_ohlcv(index, actual_start, actual_end)
        path = save_raw_index_data(index["id"], df)
        saved_paths.append(str(path))

    return saved_paths

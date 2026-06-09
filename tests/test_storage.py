from __future__ import annotations

import pandas as pd

from src.data import storage


def test_append_raw_index_data_deduplicates_dates(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "RAW_DATA_DIR", tmp_path)

    initial = pd.DataFrame(
        [
            {"date": "2026-06-01", "open": 10, "high": 11, "low": 9, "close": 10, "volume": 100},
            {"date": "2026-06-02", "open": 11, "high": 12, "low": 10, "close": 11, "volume": 110},
        ]
    )
    update = pd.DataFrame(
        [
            {"date": "2026-06-02", "open": 12, "high": 13, "low": 11, "close": 12, "volume": 120},
            {"date": "2026-06-03", "open": 13, "high": 14, "low": 12, "close": 13, "volume": 130},
        ]
    )

    storage.save_raw_index_data("asset", initial)
    _, appended_rows = storage.append_raw_index_data("asset", update)

    result = storage.load_raw_index_data("asset")
    assert appended_rows == 1
    assert result["date"].dt.strftime("%Y-%m-%d").tolist() == [
        "2026-06-01",
        "2026-06-02",
        "2026-06-03",
    ]
    assert result.loc[result["date"].dt.strftime("%Y-%m-%d") == "2026-06-02", "close"].iloc[0] == 12

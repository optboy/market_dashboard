from __future__ import annotations

import pandas as pd

from src.indicators.technical import add_all_indicators


def test_add_all_indicators_includes_ema_macd_hist_and_drawdown() -> None:
    df = pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=140),
            "open": range(100, 240),
            "high": range(101, 241),
            "low": range(99, 239),
            "close": range(100, 240),
            "volume": [1000] * 140,
        }
    )

    result = add_all_indicators(df)

    for column in ["ema20", "ema60", "macd_hist", "drawdown_pct", "mdd_120d_pct"]:
        assert column in result.columns

    latest = result.iloc[-1]
    assert latest["ema20"] > latest["ema60"]
    assert latest["macd_hist"] == latest["macd"] - latest["macd_signal"]
    assert latest["drawdown_pct"] == 0
    assert latest["mdd_120d_pct"] <= 0

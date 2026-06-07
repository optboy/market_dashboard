import pandas as pd

from src.scoring.rules import score_latest_row


def test_score_latest_row_returns_buy_bias_for_positive_setup() -> None:
    row = pd.Series(
        {
            "close": 105,
            "ma20": 100,
            "ma60": 95,
            "rsi14": 55,
            "macd": 1.2,
            "macd_signal": 0.8,
        }
    )

    result = score_latest_row(row)

    assert result.buy_score > result.sell_score
    assert result.bias == "buy_bias"
    assert result.positive_reasons

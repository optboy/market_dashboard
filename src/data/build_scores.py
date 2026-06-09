from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.data.processed import PROCESSED_SCORE_PATH
from src.data.storage import load_raw_index_data
from src.data.universe import load_asset_universe
from src.indicators.technical import add_all_indicators
from src.scoring.rules import score_latest_row


INDICATOR_OUTPUT_DIR = Path("data/processed/indicators")


def build_index_scores() -> pd.DataFrame:
    """Build indicator files and one dashboard score file from raw index data."""
    rows: list[dict] = []
    updated_at = datetime.now().isoformat(timespec="seconds")

    INDICATOR_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_SCORE_PATH.parent.mkdir(parents=True, exist_ok=True)

    universe = load_asset_universe()
    total_assets = len(universe)
    for asset_number, asset in enumerate(universe.to_dict("records"), start=1):
        try:
            raw = load_raw_index_data(asset["asset_id"])
        except FileNotFoundError:
            print(f"skip {asset['asset_id']}: raw data not found")
            continue

        indicators = add_all_indicators(_prepare_raw_data(raw))
        valid_rows = indicators.dropna(subset=["close"])
        if len(valid_rows) < 2:
            print(f"skip {asset['asset_id']}: not enough price data")
            continue

        indicators.to_csv(INDICATOR_OUTPUT_DIR / f"{asset['asset_id']}.csv", index=False)
        if asset_number <= 10 or asset_number % 25 == 0:
            print(f"processed {asset_number}/{total_assets}: {asset['asset_id']}", flush=True)

        latest = valid_rows.iloc[-1]
        previous = valid_rows.iloc[-2]
        score = score_latest_row(latest, previous)

        rows.append(
            {
                "market": asset["market"],
                "asset_type": asset.get("asset_type", "index"),
                "index_id": asset["asset_id"],
                "name": asset["name"],
                "symbol": asset["symbol"],
                "market_cap": asset.get("market_cap"),
                "last_date": latest["date"],
                "last_price": latest["close"],
                "change_pct": _calculate_change_pct(latest, previous),
                "ma20": latest.get("ma20"),
                "ma60": latest.get("ma60"),
                "ma120": latest.get("ma120"),
                "ema20": latest.get("ema20"),
                "ema60": latest.get("ema60"),
                "rsi14": latest.get("rsi14"),
                "macd": latest.get("macd"),
                "macd_signal": latest.get("macd_signal"),
                "macd_hist": latest.get("macd_hist"),
                "bb_upper": latest.get("bb_upper"),
                "bb_middle": latest.get("bb_middle"),
                "bb_lower": latest.get("bb_lower"),
                "drawdown_pct": latest.get("drawdown_pct"),
                "mdd_120d_pct": latest.get("mdd_120d_pct"),
                "volume": latest.get("volume"),
                "volume_ma20": latest.get("volume_ma20"),
                "bullish_score": score.buy_score,
                "bearish_score": score.sell_score,
                "bias": score.bias,
                "positive_reasons": json.dumps(
                    score.positive_reasons,
                    ensure_ascii=False,
                ),
                "negative_reasons": json.dumps(
                    score.negative_reasons,
                    ensure_ascii=False,
                ),
                "updated_at": updated_at,
            }
        )

    result = pd.DataFrame(rows)
    result.to_csv(PROCESSED_SCORE_PATH, index=False)
    return result


def _prepare_raw_data(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result["date"] = pd.to_datetime(result["date"])
    return result.sort_values("date").reset_index(drop=True)


def _calculate_change_pct(latest: pd.Series, previous: pd.Series) -> float:
    if previous["close"] == 0:
        return 0.0
    return ((latest["close"] - previous["close"]) / previous["close"]) * 100

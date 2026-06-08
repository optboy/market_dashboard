from pathlib import Path

import pandas as pd

from src.data.r2_storage import download_dataframe, is_r2_configured, missing_r2_settings


PROCESSED_SCORE_PATH = Path("data/processed/index_scores.csv")


def load_index_scores(path: Path = PROCESSED_SCORE_PATH) -> pd.DataFrame:
    """Load precomputed index scores for the dashboard."""
    if is_r2_configured():
        try:
            return download_dataframe("latest/index_scores.parquet")
        except Exception as exc:
            empty = _empty_scores()
            empty.attrs["load_error"] = f"R2 score load failed: {exc}"
            print(f"R2 score load failed, falling back to local CSV: {exc}")
            if not path.exists():
                return empty
    else:
        print(f"R2 is not configured. Missing: {missing_r2_settings()}")

    if not path.exists():
        empty = _empty_scores()
        empty.attrs["load_error"] = "Local processed CSV not found."
        return empty

    return pd.read_csv(path)


def _empty_scores() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "market",
            "asset_type",
            "index_id",
            "name",
            "symbol",
            "market_cap",
            "last_date",
            "last_price",
            "change_pct",
            "bullish_score",
            "bearish_score",
            "bias",
            "positive_reasons",
            "negative_reasons",
            "updated_at",
        ]
    )

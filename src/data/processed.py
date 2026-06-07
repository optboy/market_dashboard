from pathlib import Path

import pandas as pd


PROCESSED_SCORE_PATH = Path("data/processed/index_scores.csv")


def load_index_scores(path: Path = PROCESSED_SCORE_PATH) -> pd.DataFrame:
    """Load precomputed index scores for the dashboard."""
    if not path.exists():
        return pd.DataFrame(
            columns=[
                "market",
                "name",
                "last_price",
                "change_pct",
                "buy_score",
                "sell_score",
                "bias",
                "positive_reasons",
                "negative_reasons",
                "updated_at",
            ]
        )

    return pd.read_csv(path)

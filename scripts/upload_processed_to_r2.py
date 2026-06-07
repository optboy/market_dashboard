from __future__ import annotations

import pandas as pd

from src.data.r2_storage import is_r2_configured, upload_dataframe


def main() -> None:
    if not is_r2_configured():
        raise SystemExit(
            "R2 is not configured. Set R2_ENDPOINT_URL, R2_ACCESS_KEY_ID, "
            "R2_SECRET_ACCESS_KEY, and R2_BUCKET_NAME."
        )

    scores = pd.read_csv("data/processed/index_scores.csv")
    upload_dataframe(scores, "latest/index_scores.parquet")

    for asset_id in scores["index_id"].tolist():
        path = f"data/processed/indicators/{asset_id}.csv"
        indicators = pd.read_csv(path)
        upload_dataframe(indicators, f"indicators/{asset_id}.parquet")

    print(f"uploaded scores and {len(scores)} indicator files to R2")


if __name__ == "__main__":
    main()

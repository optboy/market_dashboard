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
    print("uploaded latest/index_scores.parquet", flush=True)

    asset_ids = scores["index_id"].tolist()
    uploaded = 0
    failed = 0
    for index, asset_id in enumerate(asset_ids, start=1):
        path = f"data/processed/indicators/{asset_id}.csv"
        try:
            indicators = pd.read_csv(path)
            upload_dataframe(indicators, f"indicators/{asset_id}.parquet")
            uploaded += 1
            if index <= 10 or index % 25 == 0:
                print(f"uploaded {index}/{len(asset_ids)}: {asset_id}", flush=True)
        except Exception as exc:
            failed += 1
            print(f"failed upload {asset_id}: {exc}", flush=True)

    print(f"uploaded scores and {uploaded} indicator files to R2; failed {failed}")


if __name__ == "__main__":
    main()

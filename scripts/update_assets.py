from __future__ import annotations

from datetime import date, timedelta

from src.data.downloaders import fetch_asset_ohlcv
from src.data.storage import save_raw_index_data
from src.data.universe import build_asset_universe


DEFAULT_LOOKBACK_DAYS = 365 * 2


def main() -> None:
    end_date = date.today()
    start_date = end_date - timedelta(days=DEFAULT_LOOKBACK_DAYS)
    universe = build_asset_universe()
    total = len(universe)

    saved = 0
    failed = 0
    for index, asset in enumerate(universe.to_dict("records"), start=1):
        try:
            if index <= 10 or index % 25 == 0:
                print(f"updating {index}/{total}: {asset['asset_id']} {asset['symbol']}", flush=True)
            df = fetch_asset_ohlcv(asset, start_date, end_date)
            save_raw_index_data(asset["asset_id"], df)
            saved += 1
        except Exception as exc:
            failed += 1
            print(f"failed {index}/{total}: {asset['asset_id']} {asset['symbol']}: {exc}", flush=True)

    print(f"saved {saved} assets; failed {failed} assets")


if __name__ == "__main__":
    main()

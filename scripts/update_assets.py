from __future__ import annotations

import argparse
from datetime import date, timedelta

from src.data.downloaders import fetch_asset_ohlcv
from src.data.storage import append_raw_index_data, load_raw_index_data, save_raw_index_data
from src.data.universe import build_asset_universe


DEFAULT_LOOKBACK_DAYS = 365 * 2


def main() -> None:
    parser = argparse.ArgumentParser(description="Update raw OHLCV data for configured assets.")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Download the full lookback window and overwrite existing raw files.",
    )
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=DEFAULT_LOOKBACK_DAYS,
        help="Lookback window for initial or --full downloads.",
    )
    args = parser.parse_args()

    end_date = date.today()
    universe = build_asset_universe()
    total = len(universe)

    saved = 0
    unchanged = 0
    failed = 0
    for index, asset in enumerate(universe.to_dict("records"), start=1):
        try:
            if index <= 10 or index % 25 == 0:
                print(f"updating {index}/{total}: {asset['asset_id']} {asset['symbol']}", flush=True)
            start_date = _start_date_for_asset(asset["asset_id"], end_date, args.lookback_days, args.full)
            if start_date > end_date:
                unchanged += 1
                continue
            df = fetch_asset_ohlcv(asset, start_date, end_date)
            if args.full:
                save_raw_index_data(asset["asset_id"], df)
                saved += 1
            else:
                _, appended_rows = append_raw_index_data(asset["asset_id"], df)
                if appended_rows:
                    saved += 1
                else:
                    unchanged += 1
        except Exception as exc:
            if not args.full and _is_no_new_data_error(exc) and _has_existing_raw_data(asset["asset_id"]):
                unchanged += 1
                if index <= 10 or index % 25 == 0:
                    print(f"unchanged {index}/{total}: {asset['asset_id']} {asset['symbol']}", flush=True)
                continue
            failed += 1
            print(f"failed {index}/{total}: {asset['asset_id']} {asset['symbol']}: {exc}", flush=True)

    print(f"saved {saved} assets; unchanged {unchanged} assets; failed {failed} assets")


def _start_date_for_asset(asset_id: str, end_date: date, lookback_days: int, full: bool) -> date:
    if full:
        return end_date - timedelta(days=lookback_days)

    try:
        existing = load_raw_index_data(asset_id)
    except FileNotFoundError:
        return end_date - timedelta(days=lookback_days)

    if existing.empty:
        return end_date - timedelta(days=lookback_days)

    last_date = existing["date"].max().date()
    return last_date + timedelta(days=1)


def _has_existing_raw_data(asset_id: str) -> bool:
    try:
        return not load_raw_index_data(asset_id).empty
    except FileNotFoundError:
        return False


def _is_no_new_data_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "returned no" in message or "no ohlcv data" in message


if __name__ == "__main__":
    main()

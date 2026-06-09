from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import yaml

from src.data.index_config import load_indices


UNIVERSE_PATH = Path("data/processed/universe.csv")
US_SEED_PATH = Path("config/us_seed_symbols.yaml")
US_COMPANY_NAMES_PATH = Path("config/us_company_names.yaml")
KOREA_SEED_PATH = Path("config/korea_seed_symbols.yaml")


def build_asset_universe(per_market_limit: int = 100) -> pd.DataFrame:
    rows = _index_rows()
    rows.extend(_korean_market_cap_rows("KOSPI", "kospi", per_market_limit))
    rows.extend(_korean_market_cap_rows("KOSDAQ", "kosdaq", per_market_limit))
    rows.extend(_us_seed_rows(per_market_limit))

    result = pd.DataFrame(rows).drop_duplicates(subset=["asset_id"])
    UNIVERSE_PATH.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(UNIVERSE_PATH, index=False)
    return result


def load_asset_universe() -> pd.DataFrame:
    if UNIVERSE_PATH.exists():
        return pd.read_csv(UNIVERSE_PATH)
    return pd.DataFrame(_index_rows())


def _index_rows() -> list[dict]:
    rows = []
    for index in load_indices():
        rows.append(
            {
                "asset_id": index["id"],
                "asset_type": "index",
                "market": index["market"],
                "name": index["name"],
                "symbol": index["symbol"],
                "data_provider": index["data_provider"],
                "fallback_provider": index.get("fallback_provider"),
                "fallback_symbol": index.get("fallback_symbol"),
                "market_cap": None,
            }
        )
    return rows


def _korean_market_cap_rows(market: str, market_id: str, limit: int) -> list[dict]:
    from pykrx import stock

    symbols = _korean_seed_symbols(market_id, limit)
    market_caps = {}

    rows = []
    for ticker in symbols:
        rows.append(
            {
                "asset_id": f"{market_id}_{ticker}",
                "asset_type": "stock",
                "market": market,
                "name": stock.get_market_ticker_name(ticker),
                "symbol": ticker,
                "data_provider": "pykrx",
                "fallback_provider": None,
                "fallback_symbol": None,
                "market_cap": market_caps.get(ticker),
            }
        )
    return rows


def _latest_market_cap_date(market: str) -> date:
    from pykrx import stock

    today = date.today()
    for offset in range(365):
        target = today - timedelta(days=offset)
        try:
            cap = stock.get_market_cap_by_ticker(target.strftime("%Y%m%d"), market=market)
        except Exception:
            continue
        if not cap.empty:
            return target
    raise ValueError(f"No market cap data found for {market}")


def _us_seed_rows(limit: int) -> list[dict]:
    with US_SEED_PATH.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)
    company_names = _us_company_names()

    rows = []
    for market_id, config in data["markets"].items():
        symbols = config["symbols"][:limit]
        for symbol in symbols:
            symbol = str(symbol)
            rows.append(
                {
                    "asset_id": f"{market_id}_{symbol.replace('-', '_')}",
                    "asset_type": "stock",
                    "market": config["market"],
                    "name": company_names.get(symbol, symbol),
                    "symbol": symbol,
                    "data_provider": "yfinance",
                    "fallback_provider": None,
                    "fallback_symbol": None,
                    "market_cap": None,
                }
            )
    return rows


def _us_company_names() -> dict[str, str]:
    if not US_COMPANY_NAMES_PATH.exists():
        return {}
    with US_COMPANY_NAMES_PATH.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    return {str(symbol): str(name) for symbol, name in data.get("symbols", {}).items()}


def _korean_seed_symbols(market_id: str, limit: int) -> list[str]:
    with KOREA_SEED_PATH.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)
    return data["markets"][market_id]["symbols"][:limit]

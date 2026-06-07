from __future__ import annotations

from datetime import date

import pandas as pd


OHLCV_COLUMNS = ["date", "open", "high", "low", "close", "volume"]


def fetch_index_ohlcv(index: dict, start_date: date, end_date: date) -> pd.DataFrame:
    """Fetch daily OHLCV data for one configured index."""
    provider = index["data_provider"]
    symbol = index["symbol"]

    try:
        return _fetch_with_provider(provider, symbol, start_date, end_date)
    except Exception:
        fallback_provider = index.get("fallback_provider")
        fallback_symbol = index.get("fallback_symbol")
        if fallback_provider and fallback_symbol:
            return _fetch_with_provider(
                fallback_provider,
                fallback_symbol,
                start_date,
                end_date,
            )
        raise


def _fetch_with_provider(
    provider: str,
    symbol: str,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    if provider == "pykrx":
        return fetch_pykrx_index_ohlcv(symbol, start_date, end_date)
    if provider == "yfinance":
        return fetch_yfinance_index_ohlcv(symbol, start_date, end_date)
    raise ValueError(f"Unsupported data provider: {provider}")


def fetch_pykrx_index_ohlcv(symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
    """Fetch Korean index OHLCV data from pykrx."""
    from pykrx import stock

    raw = stock.get_index_ohlcv_by_date(
        start_date.strftime("%Y%m%d"),
        end_date.strftime("%Y%m%d"),
        symbol,
        name_display=False,
    )
    if raw.empty:
        raise ValueError(f"pykrx returned no index data for {symbol}")

    df = raw.reset_index()
    df = df.rename(
        columns={
            "날짜": "date",
            "시가": "open",
            "고가": "high",
            "저가": "low",
            "종가": "close",
            "거래량": "volume",
        }
    )
    return _normalize_ohlcv(df)


def fetch_yfinance_index_ohlcv(symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
    """Fetch US index OHLCV data from yfinance."""
    import yfinance as yf

    raw = yf.download(
        symbol,
        start=start_date.isoformat(),
        end=end_date.isoformat(),
        progress=False,
        auto_adjust=False,
    )
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    raw.columns.name = None
    if raw.empty:
        raise ValueError(f"yfinance returned no index data for {symbol}")

    df = raw.reset_index()
    df = df.rename(
        columns={
            "Date": "date",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        }
    )
    return _normalize_ohlcv(df)


def _normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize provider-specific OHLCV frames to the project schema."""
    if df.empty:
        raise ValueError("No OHLCV data to normalize")

    result = df.loc[:, OHLCV_COLUMNS].copy()
    result["date"] = pd.to_datetime(result["date"]).dt.date

    for column in ["open", "high", "low", "close", "volume"]:
        result[column] = pd.to_numeric(result[column], errors="coerce")

    return result.dropna(subset=["date", "open", "high", "low", "close"])

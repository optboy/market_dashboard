import pandas as pd


def add_moving_averages(df: pd.DataFrame) -> pd.DataFrame:
    """Add common moving averages used by chart readers."""
    result = df.copy()
    result["ma20"] = result["close"].rolling(window=20).mean()
    result["ma60"] = result["close"].rolling(window=60).mean()
    result["ma120"] = result["close"].rolling(window=120).mean()
    return result


def add_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Add RSI using a simple rolling average implementation."""
    result = df.copy()
    delta = result["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss

    result["rsi14"] = 100 - (100 / (1 + rs))
    return result


def add_macd(df: pd.DataFrame) -> pd.DataFrame:
    """Add MACD and signal line."""
    result = df.copy()
    ema12 = result["close"].ewm(span=12, adjust=False).mean()
    ema26 = result["close"].ewm(span=26, adjust=False).mean()
    result["macd"] = ema12 - ema26
    result["macd_signal"] = result["macd"].ewm(span=9, adjust=False).mean()
    return result


def add_bollinger_bands(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """Add Bollinger Bands."""
    result = df.copy()
    middle = result["close"].rolling(window=window).mean()
    std = result["close"].rolling(window=window).std()
    result["bb_middle"] = middle
    result["bb_upper"] = middle + (2 * std)
    result["bb_lower"] = middle - (2 * std)
    return result


def add_volume_average(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """Add average volume."""
    result = df.copy()
    result["volume_ma20"] = result["volume"].rolling(window=window).mean()
    return result


def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add all MVP technical indicators."""
    result = add_moving_averages(df)
    result = add_rsi(result)
    result = add_macd(result)
    result = add_bollinger_bands(result)
    result = add_volume_average(result)
    return result

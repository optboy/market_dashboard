from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class ScoreResult:
    buy_score: int
    sell_score: int
    positive_reasons: list[str]
    negative_reasons: list[str]

    @property
    def bias(self) -> str:
        diff = self.buy_score - self.sell_score
        if diff >= 20:
            return "buy_bias"
        if diff <= -20:
            return "sell_bias"
        return "neutral"


def score_latest_row(row: pd.Series) -> ScoreResult:
    """Score one latest indicator row with initial placeholder rules."""
    buy_score = 0
    sell_score = 0
    positive_reasons: list[str] = []
    negative_reasons: list[str] = []

    close = row.get("close")
    ma20 = row.get("ma20")
    ma60 = row.get("ma60")
    rsi14 = row.get("rsi14")
    macd = row.get("macd")
    macd_signal = row.get("macd_signal")

    if pd.notna(close) and pd.notna(ma20):
        if close > ma20:
            buy_score += 15
            positive_reasons.append("종가가 20일 이동평균선 위에 있습니다.")
        else:
            sell_score += 15
            negative_reasons.append("종가가 20일 이동평균선 아래에 있습니다.")

    if pd.notna(ma20) and pd.notna(ma60):
        if ma20 > ma60:
            buy_score += 20
            positive_reasons.append("20일 이동평균선이 60일 이동평균선 위에 있습니다.")
        else:
            sell_score += 20
            negative_reasons.append("20일 이동평균선이 60일 이동평균선 아래에 있습니다.")

    if pd.notna(rsi14):
        if 45 <= rsi14 <= 65:
            buy_score += 10
            positive_reasons.append("RSI가 과열 없이 중립 이상의 모멘텀을 보입니다.")
        elif rsi14 > 70:
            sell_score += 10
            negative_reasons.append("RSI가 과매수 구간에 가깝습니다.")
        elif rsi14 < 30:
            buy_score += 10
            positive_reasons.append("RSI가 과매도 구간에 가깝습니다.")

    if pd.notna(macd) and pd.notna(macd_signal):
        if macd > macd_signal:
            buy_score += 15
            positive_reasons.append("MACD가 시그널선 위에 있습니다.")
        else:
            sell_score += 15
            negative_reasons.append("MACD가 시그널선 아래에 있습니다.")

    return ScoreResult(
        buy_score=min(buy_score, 100),
        sell_score=min(sell_score, 100),
        positive_reasons=positive_reasons,
        negative_reasons=negative_reasons,
    )

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import yaml


SCORING_RULES_PATH = Path("config/scoring_rules.yaml")


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


def load_scoring_rules(path: Path = SCORING_RULES_PATH) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def score_latest_row(row: pd.Series, previous_row: pd.Series | None = None) -> ScoreResult:
    """Score one latest indicator row using configurable initial rules."""
    rules = load_scoring_rules()
    weights = rules["weights"]
    thresholds = rules["thresholds"]

    buy_score = 0
    sell_score = 0
    positive_reasons: list[str] = []
    negative_reasons: list[str] = []

    close = row.get("close")
    ma20 = row.get("ma20")
    ma60 = row.get("ma60")
    ma120 = row.get("ma120")
    ema20 = row.get("ema20")
    ema60 = row.get("ema60")
    rsi14 = row.get("rsi14")
    macd = row.get("macd")
    macd_signal = row.get("macd_signal")
    macd_hist = row.get("macd_hist")
    bb_middle = row.get("bb_middle")
    drawdown_pct = row.get("drawdown_pct")
    volume = row.get("volume")
    volume_ma20 = row.get("volume_ma20")
    high = row.get("high")
    low = row.get("low")
    prev_high_20d = row.get("prev_high_20d")
    prev_low_20d = row.get("prev_low_20d")
    ma20_slope_5d = row.get("ma20_slope_5d")

    previous_close = None if previous_row is None else previous_row.get("close")
    previous_rsi = None if previous_row is None else previous_row.get("rsi14")
    previous_macd_hist = None if previous_row is None else previous_row.get("macd_hist")
    previous_low_20d = None if previous_row is None else previous_row.get("prev_low_20d")
    previous_high_20d = None if previous_row is None else previous_row.get("prev_high_20d")

    if pd.notna(close) and pd.notna(ma20):
        if close > ma20:
            buy_score += weights["trend"]["close_above_ma20"]
            positive_reasons.append("종가가 20일 이동평균선 위에 있어 단기 추세가 양호합니다.")
        else:
            sell_score += weights["trend"]["close_above_ma20"]
            negative_reasons.append("종가가 20일 이동평균선 아래에 있어 단기 추세가 약합니다.")

    if pd.notna(ma20) and pd.notna(ma60):
        if ma20 > ma60:
            buy_score += weights["trend"]["ma20_above_ma60"]
            positive_reasons.append("20일 이동평균선이 60일 이동평균선 위에 있습니다.")
        else:
            sell_score += weights["trend"]["ma20_above_ma60"]
            negative_reasons.append("20일 이동평균선이 60일 이동평균선 아래에 있습니다.")

    if pd.notna(ma60) and pd.notna(ma120):
        if ma60 > ma120:
            buy_score += weights["trend"]["ma60_above_ma120"]
            positive_reasons.append("60일 이동평균선이 120일 이동평균선 위에 있어 중기 추세가 우호적입니다.")
        else:
            sell_score += weights["trend"]["ma60_above_ma120"]
            negative_reasons.append("60일 이동평균선이 120일 이동평균선 아래에 있어 중기 추세가 약합니다.")

    if pd.notna(ma20_slope_5d):
        if ma20_slope_5d > 0:
            buy_score += weights["trend"]["ma20_slope_up"]
            positive_reasons.append("20일 이동평균선 기울기가 최근 5거래일 기준 상승 중입니다.")
        elif ma20_slope_5d < 0:
            sell_score += weights["trend"]["ma20_slope_up"]
            negative_reasons.append("20일 이동평균선 기울기가 최근 5거래일 기준 하락 중입니다.")

    if pd.notna(ema20) and pd.notna(ema60):
        if ema20 > ema60:
            buy_score += weights["trend"]["ema20_above_ema60"]
            positive_reasons.append("EMA20이 EMA60 위에 있어 단기 반응 추세가 우호적입니다.")
        else:
            sell_score += weights["trend"]["ema20_above_ema60"]
            negative_reasons.append("EMA20이 EMA60 아래에 있어 단기 반응 추세가 약합니다.")

    if pd.notna(rsi14):
        if thresholds["rsi_healthy_min"] <= rsi14 <= thresholds["rsi_healthy_max"]:
            buy_score += weights["momentum"]["rsi_healthy"]
            positive_reasons.append("RSI가 과열 없이 중립 이상의 모멘텀을 보입니다.")
        elif rsi14 > thresholds["rsi_overbought"]:
            sell_score += weights["volatility"]["overbought_oversold_risk"]
            negative_reasons.append("RSI가 과매수 구간에 가깝습니다.")
        elif rsi14 < thresholds["rsi_oversold"]:
            buy_score += weights["volatility"]["overbought_oversold_risk"]
            positive_reasons.append("RSI가 과매도 구간에 가깝습니다.")
        elif rsi14 < thresholds["rsi_weak"]:
            sell_score += weights["momentum"]["rsi_healthy"]
            negative_reasons.append("RSI가 40 아래로 모멘텀이 약한 구간입니다.")

    if pd.notna(rsi14) and pd.notna(previous_rsi):
        if rsi14 > previous_rsi:
            buy_score += weights["momentum"]["rsi_direction"]
            positive_reasons.append("RSI가 전 거래일보다 상승했습니다.")
        elif rsi14 < previous_rsi:
            sell_score += weights["momentum"]["rsi_direction"]
            negative_reasons.append("RSI가 전 거래일보다 하락했습니다.")

    if pd.notna(macd) and pd.notna(macd_signal):
        if macd > macd_signal:
            buy_score += weights["momentum"]["macd_above_signal"]
            positive_reasons.append("MACD가 시그널선 위에 있습니다.")
        else:
            sell_score += weights["momentum"]["macd_above_signal"]
            negative_reasons.append("MACD가 시그널선 아래에 있습니다.")

    if pd.notna(macd):
        if macd > 0:
            buy_score += weights["momentum"]["macd_above_zero"]
            positive_reasons.append("MACD가 0선 위에 있어 상승 모멘텀이 우세합니다.")
        elif macd < 0:
            sell_score += weights["momentum"]["macd_above_zero"]
            negative_reasons.append("MACD가 0선 아래에 있어 하락 모멘텀이 우세합니다.")

    if pd.notna(macd_hist) and pd.notna(previous_macd_hist):
        if macd_hist > previous_macd_hist:
            buy_score += weights["momentum"]["macd_hist_direction"]
            positive_reasons.append("MACD 히스토그램이 전 거래일보다 개선되었습니다.")
        elif macd_hist < previous_macd_hist:
            sell_score += weights["momentum"]["macd_hist_direction"]
            negative_reasons.append("MACD 히스토그램이 전 거래일보다 악화되었습니다.")

    if pd.notna(close) and pd.notna(bb_middle):
        if close > bb_middle:
            buy_score += weights["volatility"]["close_above_bb_middle"]
            positive_reasons.append("종가가 볼린저밴드 중단 위에 있습니다.")
        else:
            sell_score += weights["volatility"]["close_above_bb_middle"]
            negative_reasons.append("종가가 볼린저밴드 중단 아래에 있습니다.")

    if pd.notna(drawdown_pct):
        if drawdown_pct >= thresholds["mild_drawdown_pct"]:
            buy_score += weights["volatility"]["mild_drawdown"]
            positive_reasons.append("고점 대비 낙폭이 제한적이라 추세 훼손이 크지 않습니다.")
        elif drawdown_pct <= thresholds["severe_drawdown_pct"]:
            sell_score += weights["volatility"]["severe_drawdown"]
            negative_reasons.append("고점 대비 낙폭이 커서 추세 회복 부담이 있습니다.")

    if pd.notna(close) and pd.notna(high) and pd.notna(prev_high_20d) and high >= prev_high_20d:
        buy_score += weights["structure"]["breakout_20d_high"]
        positive_reasons.append("최근 20거래일 고점 돌파 신호가 있습니다.")

    if pd.notna(close) and pd.notna(low) and pd.notna(prev_low_20d) and low <= prev_low_20d:
        sell_score += weights["structure"]["breakdown_20d_low"]
        negative_reasons.append("최근 20거래일 저점 이탈 신호가 있습니다.")

    if pd.notna(prev_low_20d) and pd.notna(previous_low_20d):
        if prev_low_20d > previous_low_20d:
            buy_score += weights["structure"]["higher_low"]
            positive_reasons.append("최근 저점이 높아지는 구조입니다.")
        elif prev_low_20d < previous_low_20d:
            sell_score += weights["structure"]["higher_low"]
            negative_reasons.append("최근 저점이 낮아지는 구조입니다.")

    if pd.notna(prev_high_20d) and pd.notna(previous_high_20d):
        if prev_high_20d < previous_high_20d:
            sell_score += weights["structure"]["lower_high"]
            negative_reasons.append("최근 고점이 낮아지는 구조입니다.")

    if pd.notna(volume) and pd.notna(volume_ma20):
        high_volume = volume > volume_ma20 * thresholds["high_volume_ratio"]
        if high_volume:
            buy_score += weights["volume"]["volume_above_ma20"]
            positive_reasons.append("거래량이 20일 평균을 웃돌아 시장 참여가 증가했습니다.")

            if pd.notna(previous_close) and pd.notna(close):
                if close > previous_close:
                    buy_score += weights["volume"]["up_day_high_volume"]
                    positive_reasons.append("상승일에 거래량이 20일 평균보다 많았습니다.")
                elif close < previous_close:
                    sell_score += weights["volume"]["down_day_high_volume"]
                    negative_reasons.append("하락일에 거래량이 20일 평균보다 많았습니다.")
        else:
            negative_reasons.append("거래량이 20일 평균 이하라 신호 확인 강도는 제한적입니다.")

    return ScoreResult(
        buy_score=min(buy_score, 100),
        sell_score=min(sell_score, 100),
        positive_reasons=positive_reasons,
        negative_reasons=negative_reasons,
    )

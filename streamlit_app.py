from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

from src.data.processed import load_index_scores
from src.scoring.rules import SCORING_RULES_PATH


BIAS_LABELS = {
    "buy_bias": "상승 우위",
    "sell_bias": "하락 우위",
    "neutral": "중립",
}


st.set_page_config(
    page_title="Market Technical Score Dashboard",
    page_icon="📈",
    layout="wide",
)


def main() -> None:
    st.title("Market Technical Score Dashboard")
    st.caption("주요 지수의 기술적 지표 기반 상승/하락 시그널 점수")

    scores = load_index_scores()
    if scores.empty:
        st.info(
            "아직 생성된 분석 결과가 없습니다. "
            "`python -m scripts.build_index_scores`를 실행하면 결과가 표시됩니다."
        )
        return

    scores = _prepare_scores(scores)

    updated_at = scores["updated_at"].dropna().iloc[0]
    st.caption(f"마지막 처리 시각: {updated_at}")

    _render_summary(scores)
    _render_score_table(scores)
    _render_details(scores)
    _render_scoring_method(SCORING_RULES_PATH)


def _prepare_scores(scores: pd.DataFrame) -> pd.DataFrame:
    result = scores.copy()
    result["bias_label"] = result["bias"].map(BIAS_LABELS).fillna(result["bias"])
    result["positive_reasons_list"] = result["positive_reasons"].apply(_parse_reasons)
    result["negative_reasons_list"] = result["negative_reasons"].apply(_parse_reasons)
    result["핵심 긍정 이유"] = result["positive_reasons_list"].apply(_join_top_reasons)
    result["핵심 부정 이유"] = result["negative_reasons_list"].apply(_join_top_reasons)
    return result


def _render_summary(scores: pd.DataFrame) -> None:
    col1, col2, col3 = st.columns(3)
    col1.metric("상승 우위", int((scores["bias"] == "buy_bias").sum()))
    col2.metric("중립", int((scores["bias"] == "neutral").sum()))
    col3.metric("하락 우위", int((scores["bias"] == "sell_bias").sum()))


def _render_score_table(scores: pd.DataFrame) -> None:
    st.subheader("Index Scores")

    market_filter = st.multiselect(
        "시장 필터",
        sorted(scores["market"].unique()),
        default=sorted(scores["market"].unique()),
    )
    filtered = scores[scores["market"].isin(market_filter)].copy()

    display = filtered[
        [
            "market",
            "name",
            "last_date",
            "last_price",
            "change_pct",
            "bullish_score",
            "bearish_score",
            "bias_label",
            "핵심 긍정 이유",
            "핵심 부정 이유",
        ]
    ].rename(
        columns={
            "market": "시장",
            "name": "지수",
            "last_date": "최근 거래일",
            "last_price": "종가",
            "change_pct": "등락률(%)",
            "bullish_score": "상승 시그널 점수",
            "bearish_score": "하락 시그널 점수",
            "bias_label": "판단",
        }
    )

    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
    )


def _render_details(scores: pd.DataFrame) -> None:
    st.subheader("Index Details")
    selected_name = st.selectbox("상세 지수", scores["name"].tolist())
    row = scores[scores["name"] == selected_name].iloc[0]

    metric_cols = st.columns(5)
    metric_cols[0].metric("종가", f"{row['last_price']:,.2f}")
    metric_cols[1].metric("등락률", f"{row['change_pct']:.2f}%")
    metric_cols[2].metric("RSI 14", f"{row['rsi14']:.1f}")
    metric_cols[3].metric("상승 점수", int(row["bullish_score"]))
    metric_cols[4].metric("하락 점수", int(row["bearish_score"]))

    st.write("긍정 시그널")
    for reason in row["positive_reasons_list"]:
        st.write(f"- {reason}")

    st.write("부정/주의 시그널")
    for reason in row["negative_reasons_list"]:
        st.write(f"- {reason}")


def _render_scoring_method(path: Path) -> None:
    st.subheader("Scoring Method")
    st.caption(
        "현재 점수는 투자 추천이 아니라 기술적 지표 상태를 설명하기 위한 "
        "초기 룰 기반 점수입니다. 가중치는 추후 백테스트로 조정합니다."
    )

    with path.open("r", encoding="utf-8") as file:
        rules = yaml.safe_load(file)

    st.write("카테고리별 가중치")
    weights = []
    for category, category_weights in rules["weights"].items():
        for signal, weight in category_weights.items():
            weights.append(
                {
                    "category": category,
                    "signal": signal,
                    "weight": weight,
                }
            )

    st.dataframe(pd.DataFrame(weights), use_container_width=True, hide_index=True)

    with st.expander("원본 scoring 설정 보기"):
        st.code(yaml.safe_dump(rules, allow_unicode=True, sort_keys=False), language="yaml")


def _parse_reasons(value: str) -> list[str]:
    if not isinstance(value, str) or not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return [value]
    return parsed if isinstance(parsed, list) else [str(parsed)]


def _join_top_reasons(reasons: list[str], limit: int = 2) -> str:
    return " / ".join(reasons[:limit])


if __name__ == "__main__":
    main()

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yaml

from src.data.processed import load_index_scores
from src.data.r2_storage import download_dataframe, is_r2_configured
from src.scoring.rules import SCORING_RULES_PATH


BIAS_LABELS = {
    "buy_bias": "상승 우위",
    "sell_bias": "하락 우위",
    "neutral": "중립",
}
BIAS_COLORS = {
    "buy_bias": "#16a34a",
    "sell_bias": "#dc2626",
    "neutral": "#64748b",
}
INDICATOR_DIR = Path("data/processed/indicators")


st.set_page_config(
    page_title="Market Technical Score Dashboard",
    page_icon="📈",
    layout="wide",
)


def main() -> None:
    st.title("Market Technical Score Dashboard")
    st.caption("기술적 지표 기반 시장/종목 상태 요약")

    scores = load_scores()
    if scores.empty:
        st.info(
            "아직 생성된 분석 결과가 없습니다. "
            "`python -m scripts.build_index_scores`를 실행하면 결과가 표시됩니다."
        )
        return

    scores = prepare_scores(scores)
    updated_at = scores["updated_at"].dropna().iloc[0]

    render_market_overview(scores, updated_at)

    st.divider()
    selected_market = render_market_selector(scores)
    market_scores = scores[scores["market"] == selected_market].copy()

    selected_id = render_rankings(market_scores)
    selected_row = scores[scores["index_id"] == selected_id].iloc[0]

    st.divider()
    render_detail(selected_row)
    render_scoring_popover()


@st.cache_data
def load_scores() -> pd.DataFrame:
    return load_index_scores()


@st.cache_data
def load_indicator_data(asset_id: str) -> pd.DataFrame:
    if is_r2_configured():
        try:
            df = download_dataframe(f"indicators/{asset_id}.parquet")
            df["date"] = pd.to_datetime(df["date"])
            return df.sort_values("date").reset_index(drop=True)
        except Exception as exc:
            print(f"R2 indicator load failed for {asset_id}, falling back to local CSV: {exc}")

    path = INDICATOR_DIR / f"{asset_id}.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path, parse_dates=["date"])
    return df.sort_values("date").reset_index(drop=True)


def prepare_scores(scores: pd.DataFrame) -> pd.DataFrame:
    result = scores.copy()
    if "asset_type" not in result.columns:
        result["asset_type"] = "index"
    if "symbol" not in result.columns:
        result["symbol"] = result["index_id"]
    if "market_cap" not in result.columns:
        result["market_cap"] = None

    result["bias_label"] = result["bias"].map(BIAS_LABELS).fillna(result["bias"])
    result["net_score"] = result["bullish_score"] - result["bearish_score"]
    result["positive_reasons_list"] = result["positive_reasons"].apply(parse_reasons)
    result["negative_reasons_list"] = result["negative_reasons"].apply(parse_reasons)
    result["top_positive"] = result["positive_reasons_list"].apply(join_top_reasons)
    result["top_negative"] = result["negative_reasons_list"].apply(join_top_reasons)
    return result


def render_market_overview(scores: pd.DataFrame, updated_at: str) -> None:
    st.subheader("시장 요약")
    st.caption(f"마지막 처리 시각: {updated_at}")

    markets = sorted(scores["market"].unique())
    cols = st.columns(len(markets))
    for col, market in zip(cols, markets):
        market_scores = scores[scores["market"] == market]
        avg_net = market_scores["net_score"].mean()
        bullish_count = int((market_scores["bias"] == "buy_bias").sum())
        bearish_count = int((market_scores["bias"] == "sell_bias").sum())
        label = market_condition_label(avg_net)
        col.metric(
            market,
            label,
            delta=f"평균 net {avg_net:.1f}",
        )
        col.caption(f"상승 우위 {bullish_count} / 하락 우위 {bearish_count}")


def render_market_selector(scores: pd.DataFrame) -> str:
    markets = sorted(scores["market"].unique())
    selected = st.segmented_control(
        "시장 선택",
        markets,
        default=markets[0],
    )
    return selected or markets[0]


def render_rankings(scores: pd.DataFrame) -> str:
    left, right = st.columns([0.7, 0.3])
    with left:
        st.subheader("랭킹 및 검색")
    with right:
        st.caption("상단 10개는 정렬 기준에 따라 자동 갱신됩니다.")

    sort_options = {
        "상승 시그널 점수": "bullish_score",
        "하락 시그널 점수": "bearish_score",
        "Net Score": "net_score",
        "등락률": "change_pct",
        "RSI": "rsi14",
    }
    col1, col2, col3 = st.columns([0.3, 0.25, 0.45])
    sort_label = col1.selectbox("정렬 기준", list(sort_options.keys()))
    ascending = col2.toggle("오름차순", value=False)
    query = col3.text_input("검색", placeholder="지수/종목명 또는 ID")

    filtered = scores.copy()
    if query:
        lowered = query.lower()
        filtered = filtered[
            filtered["name"].str.lower().str.contains(lowered)
            | filtered["index_id"].str.lower().str.contains(lowered)
        ]

    filtered = filtered.sort_values(sort_options[sort_label], ascending=ascending)
    top_scores = filtered.head(10)

    st.write("Top 10")
    selected_id = None
    for _, row in top_scores.iterrows():
        clicked = render_ranking_card(row)
        if clicked:
            selected_id = row["index_id"]

    st.write("전체 목록")
    table = filtered[
        [
            "index_id",
            "name",
            "last_date",
            "last_price",
            "change_pct",
            "bullish_score",
            "bearish_score",
            "net_score",
            "bias_label",
        ]
    ].rename(
        columns={
            "index_id": "ID",
            "name": "이름",
            "last_date": "최근 거래일",
            "last_price": "종가",
            "change_pct": "등락률(%)",
            "bullish_score": "상승 점수",
            "bearish_score": "하락 점수",
            "net_score": "Net",
            "bias_label": "판단",
        }
    )
    st.dataframe(table, use_container_width=True, hide_index=True)

    options = filtered["index_id"].tolist()
    if not options:
        st.warning("검색 결과가 없습니다.")
        return scores.iloc[0]["index_id"]

    default_id = selected_id or options[0]
    return st.selectbox(
        "상세 보기 선택",
        options,
        index=options.index(default_id),
        format_func=lambda asset_id: filtered[filtered["index_id"] == asset_id].iloc[0]["name"],
    )


def render_ranking_card(row: pd.Series) -> bool:
    indicator = load_indicator_data(row["index_id"])
    color = BIAS_COLORS.get(row["bias"], "#64748b")

    with st.container(border=True):
        cols = st.columns([0.18, 0.16, 0.16, 0.18, 0.32])
        clicked = cols[0].button(row["name"], key=f"rank-{row['index_id']}")
        cols[1].metric("상승", int(row["bullish_score"]))
        cols[2].metric("하락", int(row["bearish_score"]))
        cols[3].metric("등락률", f"{row['change_pct']:.2f}%")
        if indicator.empty:
            cols[4].caption("차트 데이터 없음")
        else:
            cols[4].plotly_chart(
                build_mini_chart(indicator, color),
                use_container_width=True,
                config={"displayModeBar": False},
            )
    return clicked


def render_detail(row: pd.Series) -> None:
    st.subheader(f"{row['name']} 상세")
    indicator = load_indicator_data(row["index_id"])

    metric_cols = st.columns(6)
    metric_cols[0].metric("종가", f"{row['last_price']:,.2f}")
    metric_cols[1].metric("등락률", f"{row['change_pct']:.2f}%")
    metric_cols[2].metric("상승 점수", int(row["bullish_score"]))
    metric_cols[3].metric("하락 점수", int(row["bearish_score"]))
    metric_cols[4].metric("Net", int(row["net_score"]))
    metric_cols[5].metric("판단", row["bias_label"])

    if indicator.empty:
        st.warning("상세 차트 데이터가 없습니다.")
    else:
        st.plotly_chart(
            build_detail_chart(indicator, row),
            use_container_width=True,
            config={"displayModeBar": True},
        )

    left, right = st.columns(2)
    with left:
        st.write("긍정 시그널")
        for reason in row["positive_reasons_list"]:
            st.success(reason, icon="↗")
    with right:
        st.write("부정/주의 시그널")
        for reason in row["negative_reasons_list"]:
            st.error(reason, icon="↘")

    render_indicator_snapshot(row)


def render_indicator_snapshot(row: pd.Series) -> None:
    st.write("기술적 지표 스냅샷")
    snapshot = pd.DataFrame(
        [
            {"지표": "MA20", "값": row["ma20"]},
            {"지표": "MA60", "값": row["ma60"]},
            {"지표": "MA120", "값": row["ma120"]},
            {"지표": "RSI14", "값": row["rsi14"]},
            {"지표": "MACD", "값": row["macd"]},
            {"지표": "MACD Signal", "값": row["macd_signal"]},
            {"지표": "Bollinger Upper", "값": row["bb_upper"]},
            {"지표": "Bollinger Middle", "값": row["bb_middle"]},
            {"지표": "Bollinger Lower", "값": row["bb_lower"]},
            {"지표": "Volume MA20", "값": row["volume_ma20"]},
        ]
    )
    st.dataframe(snapshot, use_container_width=True, hide_index=True)


def render_scoring_popover() -> None:
    with st.popover("ⓘ Scoring"):
        st.caption(
            "현재 점수는 투자 추천이 아니라 기술적 지표 상태를 설명하기 위한 "
            "초기 룰 기반 점수입니다. 가중치는 추후 백테스트로 조정합니다."
        )
        with SCORING_RULES_PATH.open("r", encoding="utf-8") as file:
            rules = yaml.safe_load(file)
        weights = []
        for category, category_weights in rules["weights"].items():
            for signal, weight in category_weights.items():
                weights.append({"category": category, "signal": signal, "weight": weight})
        st.dataframe(pd.DataFrame(weights), use_container_width=True, hide_index=True)


def build_mini_chart(df: pd.DataFrame, color: str) -> go.Figure:
    recent = df.tail(60)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=recent["date"],
            y=recent["close"],
            mode="lines",
            line={"color": color, "width": 2},
            hoverinfo="skip",
        )
    )
    fig.update_layout(
        height=90,
        margin={"l": 0, "r": 0, "t": 4, "b": 0},
        xaxis={"visible": False},
        yaxis={"visible": False},
        showlegend=False,
    )
    return fig


def build_detail_chart(df: pd.DataFrame, row: pd.Series) -> go.Figure:
    recent = df.tail(180)
    signal_color = BIAS_COLORS.get(row["bias"], "#64748b")

    fig = go.Figure()
    fig.add_trace(
        go.Candlestick(
            x=recent["date"],
            open=recent["open"],
            high=recent["high"],
            low=recent["low"],
            close=recent["close"],
            name="Price",
            increasing_line_color="#16a34a",
            decreasing_line_color="#dc2626",
        )
    )
    fig.add_trace(go.Scatter(x=recent["date"], y=recent["ma20"], name="MA20", line={"color": "#2563eb"}))
    fig.add_trace(go.Scatter(x=recent["date"], y=recent["ma60"], name="MA60", line={"color": "#9333ea"}))
    fig.add_trace(go.Scatter(x=recent["date"], y=recent["ma120"], name="MA120", line={"color": "#475569"}))
    fig.add_trace(
        go.Scatter(
            x=recent["date"],
            y=recent["bb_upper"],
            name="BB Upper",
            line={"color": "#94a3b8", "dash": "dot"},
        )
    )
    fig.add_trace(
        go.Scatter(
            x=recent["date"],
            y=recent["bb_lower"],
            name="BB Lower",
            line={"color": "#94a3b8", "dash": "dot"},
            fill="tonexty",
            fillcolor="rgba(148, 163, 184, 0.12)",
        )
    )
    fig.add_annotation(
        x=recent["date"].iloc[-1],
        y=recent["close"].iloc[-1],
        text=f"{row['bias_label']} | +{int(row['bullish_score'])} / -{int(row['bearish_score'])}",
        showarrow=True,
        arrowcolor=signal_color,
        font={"color": signal_color},
    )
    fig.update_layout(
        height=520,
        margin={"l": 10, "r": 10, "t": 20, "b": 10},
        xaxis_rangeslider_visible=False,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
    )
    return fig


def parse_reasons(value: str) -> list[str]:
    if not isinstance(value, str) or not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return [value]
    return parsed if isinstance(parsed, list) else [str(parsed)]


def join_top_reasons(reasons: list[str], limit: int = 2) -> str:
    return " / ".join(reasons[:limit])


def market_condition_label(avg_net: float) -> str:
    if avg_net >= 20:
        return "상승 우위"
    if avg_net <= -20:
        return "하락 우위"
    return "혼조"


if __name__ == "__main__":
    main()

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yaml
from plotly.subplots import make_subplots

from src.data.processed import load_index_scores
from src.data.r2_storage import download_dataframe, is_r2_configured, missing_r2_settings
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
MARKET_ORDER = ["KOSPI", "KOSDAQ", "S&P 500", "Nasdaq", "Dow"]
COUNTRY_MARKETS = {
    "한국": ["KOSPI", "KOSDAQ"],
    "미국": ["S&P 500", "Nasdaq", "Dow"],
}
OVERVIEW_ASSETS = [
    "kospi",
    "kosdaq",
    "sp500",
    "nasdaq",
    "dow",
    "wti_oil",
    "us10y",
]
SIGNAL_HELP = {
    "P": "종가와 20일 이동평균선 위치",
    "MA": "20일/60일 이동평균선 배열",
    "EMA": "EMA20/EMA60 반응 추세",
    "LT": "60일/120일 이동평균선 배열",
    "RSI": "RSI14 모멘텀",
    "MACD": "MACD 히스토그램과 시그널",
    "BB": "볼린저밴드 중단 대비 위치",
    "DD": "고점 대비 낙폭",
    "VOL": "거래량 확인 강도",
}
INDICATOR_DIR = Path("data/processed/indicators")
CACHE_TTL_SECONDS = 10 * 60


st.set_page_config(
    page_title="Market Technical Score Dashboard",
    page_icon="📈",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp { font-size: 14px; }
    div[data-testid="stMetric"] { padding: 0.25rem 0; }
    div[data-testid="stMetric"] label { font-size: 0.78rem; }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] { font-size: 1.15rem; }
    div[data-testid="stMetric"] [data-testid="stMetricDelta"] { font-size: 0.78rem; }
    .compact-row {
        border-bottom: 1px solid #e5e7eb;
        padding: 0.2rem 0 0.05rem 0;
    }
    .asset-title {
        font-weight: 650;
        line-height: 1.15;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .asset-subtitle {
        color: #64748b;
        font-size: 0.76rem;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .score-line {
        font-size: 0.78rem;
        color: #334155;
        white-space: nowrap;
    }
    .signal-grid {
        display: flex;
        gap: 4px;
        flex-wrap: nowrap;
        align-items: center;
    }
    .signal-cell {
        min-width: 34px;
        padding: 3px 4px;
        border-radius: 5px;
        color: white;
        font-size: 0.70rem;
        font-weight: 700;
        text-align: center;
        line-height: 1.05;
    }
    .signal-cell-neutral {
        color: #334155;
        background: #e2e8f0;
    }
    @media (max-width: 768px) {
        .stApp { font-size: 13px; }
        .asset-title { font-size: 0.85rem; }
        .asset-subtitle, .score-line { font-size: 0.70rem; }
        .signal-cell { min-width: 29px; padding: 3px 2px; font-size: 0.64rem; }
        div[data-testid="stMetric"] [data-testid="stMetricValue"] { font-size: 0.95rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def main() -> None:
    st.title("Market Technical Score Dashboard")
    st.caption("기술적 지표 기반 시장/종목 상태 요약")
    render_cache_controls()

    scores = load_scores()
    if scores.empty:
        if scores.attrs.get("load_error"):
            st.error("R2 데이터를 불러오지 못했습니다. 잠시 후 `데이터 새로고침`을 눌러 다시 시도해 주세요.")
        else:
            st.info(
                "아직 생성된 분석 결과가 없습니다. "
                "`python -m scripts.build_index_scores`를 실행하면 결과가 표시됩니다."
            )
        render_data_source_debug(scores)
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


def render_cache_controls() -> None:
    col1, col2 = st.columns([0.82, 0.18])
    col1.caption("R2 데이터는 캐시를 사용하며, 기본적으로 10분마다 자동 갱신됩니다.")
    if col2.button("데이터 새로고침", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


def load_scores() -> pd.DataFrame:
    return load_index_scores()


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
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
    for column in ["ema20", "ema60", "macd_hist", "drawdown_pct", "mdd_120d_pct"]:
        if column not in result.columns:
            result[column] = None

    result["bias_label"] = result["bias"].map(BIAS_LABELS).fillna(result["bias"])
    result["net_score"] = result["bullish_score"] - result["bearish_score"]
    result["positive_reasons_list"] = result["positive_reasons"].apply(parse_reasons)
    result["negative_reasons_list"] = result["negative_reasons"].apply(parse_reasons)
    result["top_positive"] = result["positive_reasons_list"].apply(join_top_reasons)
    result["top_negative"] = result["negative_reasons_list"].apply(join_top_reasons)
    result["display_name"] = result.apply(format_display_name, axis=1)
    return result


def render_market_overview(scores: pd.DataFrame, updated_at: str) -> None:
    st.subheader("시장 한눈에 보기")
    st.caption(f"마지막 처리 시각: {updated_at}")

    overview_rows = scores[scores["index_id"].isin(OVERVIEW_ASSETS)].copy()
    overview_rows["overview_order"] = overview_rows["index_id"].apply(
        lambda asset_id: OVERVIEW_ASSETS.index(asset_id) if asset_id in OVERVIEW_ASSETS else 99
    )
    overview_rows = overview_rows.sort_values("overview_order")

    if not overview_rows.empty:
        cols = st.columns(min(len(overview_rows), 7))
        for col, (_, row) in zip(cols, overview_rows.iterrows()):
            label = row["bias_label"]
            col.metric(
                compact_overview_name(row),
                label,
                delta=f"1D {row['change_pct']:.2f}% · Net {row['net_score']:.0f}",
            )
            col.markdown(render_signal_grid(row, compact=True), unsafe_allow_html=True)

    market_summary = scores[scores["market"].isin(MARKET_ORDER)].copy()
    if not market_summary.empty:
        market_summary["market_order"] = market_summary["market"].apply(market_sort_key)
        summary = (
            market_summary.groupby("market", as_index=False)
            .agg(
                net_score=("net_score", "mean"),
                bullish=("bias", lambda values: int((values == "buy_bias").sum())),
                bearish=("bias", lambda values: int((values == "sell_bias").sum())),
                count=("bias", "size"),
                market_order=("market_order", "min"),
            )
            .sort_values("market_order")
        )
        st.dataframe(
            summary.assign(
                상태=summary["net_score"].apply(market_condition_label),
                상승비중=(summary["bullish"] / summary["count"] * 100).round(0).astype(int).astype(str) + "%",
            )[["market", "상태", "net_score", "상승비중", "bullish", "bearish", "count"]].rename(
                columns={
                    "market": "시장",
                    "net_score": "평균 Net",
                    "bullish": "상승 우위",
                    "bearish": "하락 우위",
                    "count": "종목 수",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )


def render_market_selector(scores: pd.DataFrame) -> str:
    available = [market for market in MARKET_ORDER if market in set(scores["market"])]
    if not available:
        available = sorted(scores["market"].unique())
    selected_country = st.segmented_control(
        "국가",
        list(COUNTRY_MARKETS.keys()),
        default="한국" if any(market in available for market in COUNTRY_MARKETS["한국"]) else "미국",
    )
    country_markets = [market for market in COUNTRY_MARKETS.get(selected_country or "한국", []) if market in available]
    markets = country_markets or available
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
        "상승 점수": "bullish_score",
        "하락 점수": "bearish_score",
        "Net Score": "net_score",
        "1D 등락률": "change_pct",
        "RSI": "rsi14",
    }
    col1, col2, col3 = st.columns([0.28, 0.18, 0.54])
    sort_label = col1.selectbox("정렬 기준", list(sort_options.keys()))
    ascending = col2.toggle("오름차순", value=False)
    query = col3.text_input("검색", placeholder="종목명, 티커, ID")

    filtered = scores.copy()
    if query:
        lowered = query.lower()
        filtered = filtered[
            filtered["name"].str.lower().str.contains(lowered)
            | filtered["symbol"].astype(str).str.lower().str.contains(lowered)
            | filtered["display_name"].str.lower().str.contains(lowered)
            | filtered["index_id"].str.lower().str.contains(lowered)
        ]

    filtered = filtered.sort_values(sort_options[sort_label], ascending=ascending)
    top_scores = filtered.head(10)

    st.write("Top 10")
    st.caption("1D는 최근 거래일 종가의 전일 대비 등락률입니다. 색상 타일은 기술지표별 긍정/부정 강도입니다.")
    selected_id = None
    for _, row in top_scores.iterrows():
        clicked = render_ranking_card(row)
        if clicked:
            selected_id = row["index_id"]

    st.write("전체 목록")
    table = filtered[
        [
            "index_id",
            "display_name",
            "last_date",
            "last_price",
            "change_pct",
            "rsi14",
            "drawdown_pct",
            "bullish_score",
            "bearish_score",
            "net_score",
            "bias_label",
        ]
    ].rename(
        columns={
            "index_id": "ID",
            "display_name": "종목",
            "last_date": "최근 거래일",
            "last_price": "종가",
            "change_pct": "1D(%)",
            "rsi14": "RSI",
            "drawdown_pct": "DD(%)",
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
        format_func=lambda asset_id: filtered[filtered["index_id"] == asset_id].iloc[0]["display_name"],
    )


def render_ranking_card(row: pd.Series) -> bool:
    indicator = load_indicator_data(row["index_id"])
    color = BIAS_COLORS.get(row["bias"], "#64748b")

    with st.container():
        st.markdown('<div class="compact-row">', unsafe_allow_html=True)
        cols = st.columns([0.14, 0.22, 0.21, 0.27, 0.16])
        clicked = cols[0].button(compact_button_label(row), key=f"rank-{row['index_id']}", use_container_width=True)
        cols[1].markdown(
            f"""
            <div class="asset-title">{row['display_name']}</div>
            <div class="asset-subtitle">{row['last_date']} · {row['bias_label']}</div>
            """,
            unsafe_allow_html=True,
        )
        cols[2].markdown(
            f"""
            <div class="score-line">Net <b>{row['net_score']:.0f}</b> · 상승 {row['bullish_score']:.0f} / 하락 {row['bearish_score']:.0f}</div>
            <div class="score-line">1D <b>{row['change_pct']:.2f}%</b> · RSI {row['rsi14']:.1f} · DD {safe_float(row.get('drawdown_pct')):.1f}%</div>
            """,
            unsafe_allow_html=True,
        )
        cols[3].markdown(render_signal_grid(row), unsafe_allow_html=True)
        if indicator.empty:
            cols[4].caption("차트 데이터 없음")
        else:
            cols[4].plotly_chart(
                build_mini_chart(indicator, color),
                use_container_width=True,
                config={"displayModeBar": False},
            )
        st.markdown("</div>", unsafe_allow_html=True)
    return clicked


def render_detail(row: pd.Series) -> None:
    st.subheader(f"{row['display_name']} 상세")
    indicator = load_indicator_data(row["index_id"])

    metric_cols = st.columns(6)
    metric_cols[0].metric("종가", f"{row['last_price']:,.2f}")
    metric_cols[1].metric("1D", f"{row['change_pct']:.2f}%")
    metric_cols[2].metric("상승 점수", int(row["bullish_score"]))
    metric_cols[3].metric("하락 점수", int(row["bearish_score"]))
    metric_cols[4].metric("Net", int(row["net_score"]))
    metric_cols[5].metric("판단", row["bias_label"])

    st.markdown(render_signal_grid(row, show_help=True), unsafe_allow_html=True)

    if indicator.empty:
        st.warning("상세 차트 데이터가 없습니다.")
    else:
        st.plotly_chart(
            build_detail_chart(indicator, row),
            use_container_width=True,
            config={"displayModeBar": True},
        )

    render_indicator_snapshot(row)

    with st.expander("문장형 시그널 보기"):
        left, right = st.columns(2)
        with left:
            st.write("긍정 시그널")
            for reason in row["positive_reasons_list"]:
                st.success(reason, icon="↗")
        with right:
            st.write("부정/주의 시그널")
            for reason in row["negative_reasons_list"]:
                st.error(reason, icon="↘")


def render_indicator_snapshot(row: pd.Series) -> None:
    st.write("기술적 지표 스냅샷")
    snapshot = pd.DataFrame(
        [
            {"지표": "MA20", "값": row["ma20"], "해석": signal_status_text(row, "P")},
            {"지표": "MA60", "값": row["ma60"], "해석": signal_status_text(row, "MA")},
            {"지표": "MA120", "값": row["ma120"], "해석": signal_status_text(row, "LT")},
            {"지표": "EMA20", "값": row["ema20"], "해석": signal_status_text(row, "EMA")},
            {"지표": "EMA60", "값": row["ema60"], "해석": ""},
            {"지표": "RSI14", "값": row["rsi14"], "해석": signal_status_text(row, "RSI")},
            {"지표": "MACD", "값": row["macd"], "해석": signal_status_text(row, "MACD")},
            {"지표": "MACD Signal", "값": row["macd_signal"], "해석": ""},
            {"지표": "MACD Hist", "값": row["macd_hist"], "해석": ""},
            {"지표": "BB Upper", "값": row["bb_upper"], "해석": ""},
            {"지표": "BB Middle", "값": row["bb_middle"], "해석": signal_status_text(row, "BB")},
            {"지표": "BB Lower", "값": row["bb_lower"], "해석": ""},
            {"지표": "Drawdown %", "값": row["drawdown_pct"], "해석": signal_status_text(row, "DD")},
            {"지표": "MDD 120D %", "값": row["mdd_120d_pct"], "해석": ""},
            {"지표": "Volume MA20", "값": row["volume_ma20"], "해석": signal_status_text(row, "VOL")},
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


def render_data_source_debug(scores: pd.DataFrame) -> None:
    with st.expander("데이터 연결 진단"):
        st.write(f"R2 configured: `{is_r2_configured()}`")
        missing = missing_r2_settings()
        if missing:
            st.write("Missing R2 settings:")
            for name in missing:
                st.write(f"- `{name}`")
        error = scores.attrs.get("load_error")
        if error:
            st.write("Load error:")
            st.code(error)


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
        height=52,
        margin={"l": 0, "r": 0, "t": 4, "b": 0},
        xaxis={"visible": False},
        yaxis={"visible": False},
        showlegend=False,
    )
    return fig


def build_detail_chart(df: pd.DataFrame, row: pd.Series) -> go.Figure:
    recent = df.tail(180)
    signal_color = BIAS_COLORS.get(row["bias"], "#64748b")

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.74, 0.26],
    )
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
        ),
        row=1,
        col=1,
    )
    fig.add_trace(go.Scatter(x=recent["date"], y=recent["ma20"], name="MA20", line={"color": "#2563eb"}), row=1, col=1)
    fig.add_trace(go.Scatter(x=recent["date"], y=recent["ma60"], name="MA60", line={"color": "#9333ea"}), row=1, col=1)
    fig.add_trace(go.Scatter(x=recent["date"], y=recent["ma120"], name="MA120", line={"color": "#475569"}), row=1, col=1)
    if "ema20" in recent.columns:
        fig.add_trace(
            go.Scatter(x=recent["date"], y=recent["ema20"], name="EMA20", line={"color": "#0f766e", "dash": "dash"}),
            row=1,
            col=1,
        )
    if "ema60" in recent.columns:
        fig.add_trace(
            go.Scatter(x=recent["date"], y=recent["ema60"], name="EMA60", line={"color": "#f97316", "dash": "dash"}),
            row=1,
            col=1,
        )
    fig.add_trace(
        go.Scatter(
            x=recent["date"],
            y=recent["bb_upper"],
            name="BB Upper",
            line={"color": "#94a3b8", "dash": "dot"},
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=recent["date"],
            y=recent["bb_lower"],
            name="BB Lower",
            line={"color": "#94a3b8", "dash": "dot"},
            fill="tonexty",
            fillcolor="rgba(148, 163, 184, 0.12)",
        ),
        row=1,
        col=1,
    )
    if "macd_hist" in recent.columns:
        hist_colors = ["#16a34a" if value >= 0 else "#dc2626" for value in recent["macd_hist"].fillna(0)]
        fig.add_trace(
            go.Bar(
                x=recent["date"],
                y=recent["macd_hist"],
                name="MACD Hist",
                marker_color=hist_colors,
                opacity=0.55,
            ),
            row=2,
            col=1,
        )
    fig.add_trace(
        go.Scatter(x=recent["date"], y=recent["macd"], name="MACD", line={"color": "#2563eb", "width": 1.5}),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(x=recent["date"], y=recent["macd_signal"], name="Signal", line={"color": "#f97316", "width": 1.5}),
        row=2,
        col=1,
    )
    fig.add_annotation(
        x=recent["date"].iloc[-1],
        y=recent["close"].iloc[-1],
        text=f"{row['bias_label']} | +{int(row['bullish_score'])} / -{int(row['bearish_score'])}",
        showarrow=True,
        arrowcolor=signal_color,
        font={"color": signal_color},
        row=1,
        col=1,
    )
    fig.update_layout(
        height=520,
        margin={"l": 10, "r": 10, "t": 20, "b": 10},
        xaxis_rangeslider_visible=False,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
    )
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="MACD", row=2, col=1)
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


def format_display_name(row: pd.Series) -> str:
    symbol = str(row.get("symbol") or "")
    name = str(row.get("name") or symbol)
    if symbol and name and name != symbol and row.get("asset_type") == "stock":
        return f"{symbol} · {name}"
    return name


def compact_button_label(row: pd.Series) -> str:
    symbol = str(row.get("symbol") or row["index_id"])
    if row.get("asset_type") == "stock":
        return symbol[:10]
    return str(row["name"])[:10]


def compact_overview_name(row: pd.Series) -> str:
    names = {
        "kospi": "KOSPI",
        "kosdaq": "KOSDAQ",
        "sp500": "S&P 500",
        "nasdaq": "Nasdaq",
        "dow": "Dow",
        "wti_oil": "WTI",
        "us10y": "US10Y",
    }
    return names.get(row["index_id"], row["name"])


def market_sort_key(market: str) -> int:
    try:
        return MARKET_ORDER.index(market)
    except ValueError:
        return len(MARKET_ORDER)


def render_signal_grid(row: pd.Series, compact: bool = False, show_help: bool = False) -> str:
    cells = []
    for signal in SIGNAL_HELP:
        direction, strength = signal_strength(row, signal)
        title = SIGNAL_HELP[signal]
        if show_help:
            title = f"{signal}: {title} - {signal_status_text(row, signal)}"
        css_class = "signal-cell"
        style = f"background:{signal_color(direction, strength)};"
        if direction == "neutral":
            css_class += " signal-cell-neutral"
            style = ""
        label = signal if compact else f"{signal}<br>{strength}"
        cells.append(f'<span class="{css_class}" style="{style}" title="{title}">{label}</span>')
    return f'<div class="signal-grid">{"".join(cells)}</div>'


def signal_strength(row: pd.Series, signal: str) -> tuple[str, int]:
    close = safe_float(row.get("last_price"))
    change_pct = safe_float(row.get("change_pct"))
    ma20 = safe_float(row.get("ma20"))
    ma60 = safe_float(row.get("ma60"))
    ma120 = safe_float(row.get("ma120"))
    ema20 = safe_float(row.get("ema20"))
    ema60 = safe_float(row.get("ema60"))
    rsi = safe_float(row.get("rsi14"))
    macd = safe_float(row.get("macd"))
    macd_signal = safe_float(row.get("macd_signal"))
    macd_hist = safe_float(row.get("macd_hist"))
    bb_middle = safe_float(row.get("bb_middle"))
    drawdown_pct = safe_float(row.get("drawdown_pct"))
    volume = safe_float(row.get("volume"))
    volume_ma20 = safe_float(row.get("volume_ma20"))

    if signal == "P":
        return ratio_signal(close, ma20, threshold_pct=5)
    if signal == "MA":
        return ratio_signal(ma20, ma60, threshold_pct=4)
    if signal == "EMA":
        return ratio_signal(ema20, ema60, threshold_pct=4)
    if signal == "LT":
        return ratio_signal(ma60, ma120, threshold_pct=5)
    if signal == "RSI":
        if pd.isna(rsi):
            return "neutral", 0
        if 45 <= rsi <= 55:
            return "neutral", int(abs(rsi - 50) / 5 * 2)
        direction = "bullish" if rsi > 55 else "bearish"
        return direction, clamp_strength(abs(rsi - 50) / 20 * 4)
    if signal == "MACD":
        if pd.notna(macd_hist):
            direction = "bullish" if macd_hist >= 0 else "bearish"
            return direction, clamp_strength(abs(macd_hist) / max(abs(close), 1) * 100 * 20 + 1)
        if pd.isna(macd) or pd.isna(macd_signal):
            return "neutral", 0
        direction = "bullish" if macd >= macd_signal else "bearish"
        base = abs(macd - macd_signal) / max(abs(close), 1) * 100
        bonus = 1 if (macd > 0 and direction == "bullish") or (macd < 0 and direction == "bearish") else 0
        return direction, clamp_strength(base * 10 + bonus)
    if signal == "BB":
        return ratio_signal(close, bb_middle, threshold_pct=4)
    if signal == "DD":
        if pd.isna(drawdown_pct):
            return "neutral", 0
        if drawdown_pct >= -3:
            return "bullish", 1
        if drawdown_pct >= -10:
            return "neutral", clamp_strength(abs(drawdown_pct) / 10 * 2)
        return "bearish", clamp_strength(abs(drawdown_pct) / 25 * 4)
    if signal == "VOL":
        if pd.isna(volume) or pd.isna(volume_ma20) or volume_ma20 == 0:
            return "neutral", 0
        ratio = volume / volume_ma20
        if ratio < 0.9:
            return "neutral", 1
        direction = "bullish" if change_pct >= 0 else "bearish"
        return direction, clamp_strength((ratio - 0.9) / 0.6 * 4)
    return "neutral", 0


def ratio_signal(left: float, right: float, threshold_pct: float) -> tuple[str, int]:
    if pd.isna(left) or pd.isna(right) or right == 0:
        return "neutral", 0
    pct = (left - right) / abs(right) * 100
    if abs(pct) < 0.2:
        return "neutral", 0
    return ("bullish" if pct > 0 else "bearish"), clamp_strength(abs(pct) / threshold_pct * 4)


def signal_color(direction: str, strength: int) -> str:
    alpha = 0.28 + min(max(strength, 0), 4) * 0.15
    if direction == "bullish":
        return f"rgba(22, 163, 74, {alpha:.2f})"
    if direction == "bearish":
        return f"rgba(220, 38, 38, {alpha:.2f})"
    return "#e2e8f0"


def signal_status_text(row: pd.Series, signal: str) -> str:
    direction, strength = signal_strength(row, signal)
    direction_text = {"bullish": "긍정", "bearish": "부정", "neutral": "중립"}[direction]
    return f"{direction_text} {strength}/4"


def safe_float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def clamp_strength(value: float) -> int:
    if pd.isna(value):
        return 0
    return max(1, min(4, int(round(value))))


def market_condition_label(avg_net: float) -> str:
    if avg_net >= 20:
        return "상승 우위"
    if avg_net <= -20:
        return "하락 우위"
    return "혼조"


if __name__ == "__main__":
    main()

import streamlit as st

from src.data.processed import load_index_scores


st.set_page_config(
    page_title="Market Technical Score Dashboard",
    page_icon="📈",
    layout="wide",
)


def main() -> None:
    st.title("Market Technical Score Dashboard")
    st.caption("주요 지수의 기술적 지표 기반 매수/매도 스코어 대시보드")

    scores = load_index_scores()

    if scores.empty:
        st.info(
            "아직 생성된 분석 결과가 없습니다. "
            "`data/processed/index_scores.csv`가 생성되면 이 화면에 표시됩니다."
        )
        return

    st.dataframe(
        scores,
        use_container_width=True,
        hide_index=True,
    )


if __name__ == "__main__":
    main()

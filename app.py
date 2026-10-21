import pandas as pd
import streamlit as st
import plotly.express as px

# ==========================================
# 1. 페이지 설정
# ==========================================
st.set_page_config(
    page_title="철도 설비 AI 분석",
    page_icon="🚆",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 2. 데이터 읽기
# ==========================================
@st.cache_data
def load_data():
    data = pd.read_csv("analysis_result.csv")
    data["측정시각"] = pd.to_datetime(data["측정시각"])
    data["목표시각"] = pd.to_datetime(data["목표시각"])
    return data

df = load_data()

# ==========================================
# 3. 사이드바 - 조회 조건
# ==========================================
st.sidebar.header("🔎 조회 조건")

equipment = st.sidebar.selectbox(
    "설비 선택",
    df["설비ID"].unique()
)

equipment_df = df[
    df["설비ID"] == equipment
].copy()

min_date = equipment_df["측정시각"].min().date()
max_date = equipment_df["측정시각"].max().date()

start = st.sidebar.date_input(
    "시작일",
    min_date
)

end = st.sidebar.date_input(
    "종료일",
    max_date
)

if start > end:
    st.sidebar.error("시작일이 종료일보다 늦습니다.")
    st.stop()

# 기간 필터링
view = equipment_df[
    (equipment_df["측정시각"].dt.date >= start) &
    (equipment_df["측정시각"].dt.date <= end)
].copy()

view = view.sort_values("측정시각")

st.sidebar.divider()
st.sidebar.caption(
    "설비와 조회 기간을 변경하면 분석 결과가 자동으로 갱신됩니다."
)

# ==========================================
# 4. 메인 제목
# ==========================================
st.title("🚆 철도 설비 AI 분석 대시보드")

st.caption(
    "설비 상태 모니터링 · AI 점검 후보 분석 · 온도 예측"
)

if view.empty:
    st.warning("조회 결과가 없습니다. 조회 조건을 변경하세요.")
    st.stop()

# ==========================================
# 5. 공통 분석 데이터 계산
# ==========================================
candidates = view[
    view["AI결과"] == "확인후보"
].copy()

pred = view.dropna(
    subset=["다음온도_C", "AI예측온도_C"]
).copy()

if not pred.empty:
    pred["예측오차_C"] = (
        pred["다음온도_C"] -
        pred["AI예측온도_C"]
    ).abs()

    mae = pred["예측오차_C"].mean()

else:
    mae = float("nan")

candidate_rate = (
    len(candidates) / len(view) * 100
)

# ==========================================
# 6. 상단 핵심 요약 지표
# ==========================================
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "📊 조회 건수",
        f"{len(view):,}건"
    )

with col2:
    st.metric(
        "🔴 AI 확인후보",
        f"{len(candidates):,}건"
    )

with col3:
    st.metric(
        "📌 확인후보 비율",
        f"{candidate_rate:.1f}%"
    )

with col4:
    st.metric(
        "🌡️ 예측 MAE",
        f"{mae:.2f} ℃" if not pred.empty else "자료 없음"
    )

st.divider()

# ==========================================
# 7. 탭 구성
# ==========================================
tab1, tab2, tab3 = st.tabs([
    "🔍 AI 점검 후보",
    "📈 다음 1시간 온도 예측",
    "📝 업무 검토 및 저장"
])

# ==========================================
# 탭 1 : AI 점검 후보
# ==========================================
with tab1:

    st.subheader("AI 점검 후보 분석")

    # 좌측: 온도 추이 / 우측: 분석 결과
    left, right = st.columns([3, 1])

    with left:
        fig = px.line(
            view,
            x="측정시각",
            y="온도_C",
            title="온도 추이와 AI 확인후보"
        )

        fig.add_scatter(
            x=candidates["측정시각"],
            y=candidates["온도_C"],
            mode="markers",
            name="AI 확인후보",
            marker=dict(
                color="red",
                size=10
            )
        )

        fig.update_layout(
            height=380,
            margin=dict(l=10, r=10, t=50, b=20),
            xaxis_title="측정시각",
            yaxis_title="온도 (℃)"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    with right:
        st.markdown("#### AI 분석 결과")

        result_count = (
            view["AI결과"]
            .value_counts()
            .reset_index()
        )

        result_count.columns = ["AI결과", "건수"]

        st.dataframe(
            result_count,
            hide_index=True,
            use_container_width=True
        )

        st.metric(
            "확인후보 건수",
            f"{len(candidates)}건"
        )

        st.info(
            "AI 확인후보는 점검이 필요한 가능성을 의미하며, "
            "실제 고장 확정은 아닙니다."
        )

    st.markdown("#### 확인후보 상세 목록")

    if candidates.empty:
        st.success("선택한 기간에 AI 확인후보가 없습니다.")
    else:
        st.dataframe(
            candidates,
            use_container_width=True,
            hide_index=True
        )

    # 전체 데이터는 필요할 때만 확인
    with st.expander("📋 전체 조회 데이터 보기"):
        st.dataframe(
            view,
            use_container_width=True,
            hide_index=True
        )

# ==========================================
# 탭 2 : 다음 1시간 온도 예측
# ==========================================
with tab2:

    st.subheader("다음 1시간 온도 예측 분석")

    if not pred.empty:

        col1, col2 = st.columns(2)

        with col1:
            st.metric(
                "평균 절대 오차 (MAE)",
                f"{mae:.2f} ℃"
            )

        with col2:
            st.metric(
                "예측 비교 건수",
                f"{len(pred)}건"
            )

        fig2 = px.line(
            pred,
            x="목표시각",
            y=[
                "다음온도_C",
                "AI예측온도_C"
            ],
            title="실제 온도와 AI 예측 온도 비교"
        )

        fig2.update_layout(
            height=420,
            margin=dict(l=10, r=10, t=50, b=20),
            xaxis_title="목표시각",
            yaxis_title="온도 (℃)",
            legend_title_text="구분"
        )

        st.plotly_chart(
            fig2,
            use_container_width=True
        )

        with st.expander("📋 예측 비교 상세 데이터"):
            st.dataframe(
                pred[
                    [
                        "목표시각",
                        "다음온도_C",
                        "AI예측온도_C",
                        "예측오차_C"
                    ]
                ],
                use_container_width=True,
                hide_index=True
            )

    else:
        st.warning("온도 예측 비교 데이터가 없습니다.")

# ==========================================
# 탭 3 : 업무 검토 및 저장
# ==========================================
with tab3:

    st.subheader("업무 검토 및 보고서")

    left, right = st.columns([1, 1])

    with left:
        st.markdown("#### 업무 검토 메모")

        note = st.text_area(
            "확인할 사항 및 조치 제안",
            "센서 상태와 운전 조건을 확인한 후 담당자 검토가 필요합니다.",
            height=200
        )

    with right:
        st.markdown("#### 보고서 미리보기")

        mae_text = (
            f"{mae:.2f} ℃"
            if not pred.empty
            else "자료 없음"
        )

        report = f"""철도 설비 AI 분석 보고서

설비: {equipment}
조회 기간: {start} ~ {end}
조회 건수: {len(view)}건

AI 확인후보: {len(candidates)}건
확인후보 비율: {candidate_rate:.1f}%

온도 예측 MAE: {mae_text}
예측 비교 건수: {len(pred)}건

업무 메모:
{note}

※ 교육용 가상 자료입니다.
AI 확인후보는 고장 확정이 아닙니다.
"""

        st.text(report)

    st.divider()

    st.markdown("#### 📥 파일 다운로드")

    down1, down2, down3 = st.columns(3)

    with down1:
        st.download_button(
            "조회 결과 CSV",
            view.to_csv(index=False).encode("utf-8-sig"),
            "dashboard_result.csv",
            mime="text/csv",
            use_container_width=True
        )

    with down2:
        st.download_button(
            "점검 후보 CSV",
            candidates.to_csv(index=False).encode("utf-8-sig"),
            "inspection_candidates.csv",
            mime="text/csv",
            use_container_width=True
        )

    with down3:
        st.download_button(
            "보고서 TXT",
            report.encode("utf-8-sig"),
            "dashboard_report.txt",
            mime="text/plain",
            use_container_width=True
        )

"""
app.py
메인 진입점 - 화면 흐름 제어만 담당
"""
import streamlit as st
import pandas as pd
from datetime import date

from parser import extract_records
from calculator import get_base_period, calculate_total, get_verdict
from ui import inject_css, render_gnb, render_page_title, render_kpi_cards, render_verdict, render_section_label

st.set_page_config(
    page_title="감리실적 계산기",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

inject_css()
render_gnb()
render_page_title()

# ── 입력 패널 ────────────────────────────────────────────────
st.markdown('<div class="input-panel"><div class="panel-label">입력 정보</div>', unsafe_allow_html=True)

col_date, col_upload, col_btn = st.columns([1, 2, 1], gap="large")

with col_date:
    bid_date = st.date_input("입찰 공고일", value=date.today(), format="YYYY.MM.DD")
    d_start, d_end = get_base_period(bid_date)
    st.markdown(f"""
    <div class="range-chip">
        <span class="range-chip-label">실적 기준 기간</span>
        <span class="range-chip-value">{d_start.strftime('%Y.%m.%d')} ~ {d_end.strftime('%Y.%m.%d')}</span>
    </div>
    """, unsafe_allow_html=True)

with col_upload:
    uploaded_file = st.file_uploader(
        "공사감리용역수행현황확인서 PDF",
        type=["pdf"],
        help="전력기술인단체에서 발급받은 확인서 PDF를 업로드하세요",
    )

with col_btn:
    st.markdown("<br><br>", unsafe_allow_html=True)
    calc_btn = st.button("계산 시작  →", type="primary", use_container_width=True)

st.markdown("</div>", unsafe_allow_html=True)  # input-panel

# ── 계산 및 결과 ────────────────────────────────────────────
if calc_btn:
    if not uploaded_file:
        st.error("PDF 파일을 먼저 업로드해 주세요.")
        st.stop()

    with st.spinner("PDF 분석 중..."):
        records, warnings = extract_records(uploaded_file)

    if warnings:
        with st.expander(f"파싱 경고 {len(warnings)}건"):
            for w in warnings:
                st.caption(w)

    if not records:
        st.error("유효한 데이터를 찾지 못했습니다. PDF 표 구조를 확인해 주세요.")
        st.stop()

    result_rows, total_area = calculate_total(records, d_start, d_end)
    verdict = get_verdict(total_area)

    # KPI 카드
    render_section_label("요약 통계")
    render_kpi_cards(
        total_records=len(records),
        valid_count=len(result_rows),
        field_count=len(set(r["분야"] for r in records)),
        total_area=total_area,
        is_pass=verdict["pass"],
    )

    # 판정 결과
    render_section_label("최종 판정")
    render_verdict(verdict, total_area)
    if verdict["pass"]:
        st.balloons()

    # 상세 테이블
    if result_rows:
        render_section_label("상세 계산 결과")
        df = pd.DataFrame(result_rows)
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "분야":         st.column_config.TextColumn("분야",        width="small"),
                "연면적(㎡)":   st.column_config.TextColumn("연면적(㎡)",  width="medium"),
                "이행비율":     st.column_config.TextColumn("이행비율",    width="small"),
                "감리 시작일":  st.column_config.TextColumn("감리 시작일", width="medium"),
                "감리 종료일":  st.column_config.TextColumn("감리 종료일", width="medium"),
                "중첩일수":     st.column_config.NumberColumn("중첩일수",  width="small"),
                "전체일수":     st.column_config.NumberColumn("전체일수",  width="small"),
                "기여면적(㎡)": st.column_config.NumberColumn("기여면적(㎡)", format="%.2f", width="medium"),
            },
        )

st.markdown("</div>", unsafe_allow_html=True)  # main-wrap

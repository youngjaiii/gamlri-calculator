"""
app.py
메인 진입점
- 탭으로 '연면적 계산' / '용역비 계산' 모드 선택
- 화면 흐름 제어만 담당, 로직은 각 모듈에 위임
"""
import streamlit as st
import pandas as pd
from datetime import date

from parser import extract_records
from calculator import get_base_period, calculate_area, calculate_fee
from ui import (inject_css, render_gnb, render_page_title, render_range_chip,
                render_kpi_grid, render_verdict, render_section_label)

st.set_page_config(
    page_title="감리실적 계산기",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

inject_css()

# ── 탭으로 모드 선택 ─────────────────────────────────────────
tab_area, tab_fee = st.tabs(["📐 연면적 계산", "💰 용역비 계산"])


# ══════════════════════════════════════════════════════════════
# 공통 입력 렌더링 함수
# ══════════════════════════════════════════════════════════════
def render_input_panel(mode: str) -> tuple:
    """
    공통 입력 패널 렌더링
    mode: "area" | "fee"
    Returns: (bid_date, goal, uploaded_file, calc_btn)
    """
    goal_label = "목표 연면적 (㎡)" if mode == "area" else "목표 용역비 (천원)"
    goal_default = 360_000.0 if mode == "area" else 0.0
    goal_help = "기준 충족 여부 판단에 사용됩니다 (기본값 360,000 ㎡)" if mode == "area" else "목표 용역비를 천원 단위로 입력하세요"

    st.markdown('<div class="input-panel"><div class="panel-label">입력 정보</div>', unsafe_allow_html=True)

    col_date, col_goal, col_upload, col_btn = st.columns([1, 1, 2, 1], gap="large")

    with col_date:
        bid_date = st.date_input(
            "입찰 공고일",
            value=date.today(),
            format="YYYY.MM.DD",
            key=f"bid_date_{mode}",
        )
        d_start, d_end = get_base_period(bid_date)
        render_range_chip(d_start, d_end)

    with col_goal:
        goal = st.number_input(
            goal_label,
            min_value=0.0,
            value=goal_default,
            step=10_000.0,
            format="%.0f",
            help=goal_help,
            key=f"goal_{mode}",
        )

    with col_upload:
        uploaded_file = st.file_uploader(
            "공사감리용역수행현황확인서 PDF",
            type=["pdf"],
            help="전력기술인단체에서 발급받은 확인서 PDF를 업로드하세요",
            key=f"upload_{mode}",
        )

    with col_btn:
        st.markdown("<br><br>", unsafe_allow_html=True)
        calc_btn = st.button(
            "계산 시작  →",
            type="primary",
            use_container_width=True,
            key=f"btn_{mode}",
        )

    st.markdown("</div>", unsafe_allow_html=True)
    return bid_date, goal, uploaded_file, calc_btn


# ══════════════════════════════════════════════════════════════
# 공통 결과 렌더링 함수
# ══════════════════════════════════════════════════════════════
def render_results(records, result_rows, total_value, verdict, unit: str, value_col: str):
    """
    KPI · 판정 · 상세 테이블 렌더링
    unit      : 단위 표시 문자열 (예: "㎡", "천원")
    value_col : 테이블의 환산값 컬럼명
    """
    if warnings := st.session_state.get("warnings", []):
        with st.expander(f"파싱 경고 {len(warnings)}건"):
            for w in warnings:
                st.caption(w)

    if not records:
        st.error("유효한 데이터를 찾지 못했습니다. PDF 표 구조를 확인해 주세요.")
        return

    # 요약 KPI
    render_section_label("요약 통계")
    render_kpi_grid(
        total_records=len(records),
        valid_count=len(result_rows),
        field_count=len(set(r["분야"] for r in records)),
        total_value=total_value,
        unit=unit,
        is_pass=verdict["pass"],
    )

    # 판정 결과
    render_section_label("최종 판정")
    render_verdict(verdict, total_value, unit)
    if verdict["pass"]:
        st.balloons()

    # 상세 테이블
    if result_rows:
        render_section_label("상세 계산 결과")
        df = pd.DataFrame(result_rows)

        # 환산값 컬럼 숫자 포맷 설정
        col_cfg = {
            "용역명":      st.column_config.TextColumn("용역명",      width="large"),
            "분야":        st.column_config.TextColumn("분야",        width="small"),
            "감리 시작일": st.column_config.TextColumn("감리 시작일", width="medium"),
            "감리 종료일": st.column_config.TextColumn("감리 종료일", width="medium"),
            "중첩일수":    st.column_config.NumberColumn("중첩일수",   width="small"),
            "전체일수":    st.column_config.NumberColumn("전체일수",   width="small"),
            value_col:     st.column_config.NumberColumn(value_col,   format="%.2f", width="medium"),
        }
        st.dataframe(df, use_container_width=True, hide_index=True, column_config=col_cfg)


# ══════════════════════════════════════════════════════════════
# 탭 1: 연면적 계산
# ══════════════════════════════════════════════════════════════
with tab_area:
    render_gnb("연면적 계산 모드")
    st.markdown('<div class="main-wrap">', unsafe_allow_html=True)
    render_page_title(
        "연면적 실적 계산",
        "환산면적 = 연면적 × 이행비율 × (중첩일수 / 전체감리일수)"
    )

    bid_date, goal, uploaded_file, calc_btn = render_input_panel("area")

    if calc_btn:
        if not uploaded_file:
            st.error("PDF 파일을 먼저 업로드해 주세요.")
        else:
            with st.spinner("PDF 분석 중..."):
                records, warnings = extract_records(uploaded_file)
                st.session_state["warnings"] = warnings

            d_start, d_end = get_base_period(bid_date)
            result_rows, total, verdict = calculate_area(records, d_start, d_end, goal)

            render_results(
                records=records,
                result_rows=result_rows,
                total_value=total,
                verdict=verdict,
                unit="㎡",
                value_col="환산면적(㎡)",
            )

    st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# 탭 2: 용역비 계산
# ══════════════════════════════════════════════════════════════
with tab_fee:
    render_gnb("용역비 계산 모드")
    st.markdown('<div class="main-wrap">', unsafe_allow_html=True)
    render_page_title(
        "용역비 실적 계산",
        "환산용역비 = 용역비 × (중첩일수 / 전체감리일수)"
    )

    bid_date, goal, uploaded_file, calc_btn = render_input_panel("fee")

    if calc_btn:
        if not uploaded_file:
            st.error("PDF 파일을 먼저 업로드해 주세요.")
        else:
            with st.spinner("PDF 분석 중..."):
                records, warnings = extract_records(uploaded_file)
                st.session_state["warnings"] = warnings

            d_start, d_end = get_base_period(bid_date)
            result_rows, total, verdict = calculate_fee(records, d_start, d_end, goal)

            render_results(
                records=records,
                result_rows=result_rows,
                total_value=total,
                verdict=verdict,
                unit="천원",
                value_col="환산용역비(천원)",
            )

    st.markdown("</div>", unsafe_allow_html=True)

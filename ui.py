"""
ui.py
Streamlit CSS 주입 및 UI 컴포넌트 모음
"""
import streamlit as st
from calculator import AREA_THRESHOLD


def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

    *, *::before, *::after { box-sizing: border-box; }

    html, body,
    [data-testid="stAppViewContainer"],
    [data-testid="stApp"] {
        background-color: #f5f6fa !important;
        font-family: 'Noto Sans KR', sans-serif !important;
        color: #1a1d23 !important;
    }
    [data-testid="stHeader"]  { display: none !important; }
    [data-testid="stToolbar"] { display: none !important; }
    .block-container          { padding: 0 !important; max-width: 100% !important; }

    .gnb {
        background: #ffffff;
        border-bottom: 1px solid #e8eaed;
        padding: 0 3rem;
        height: 60px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .gnb-logo {
        display: flex; align-items: center; gap: 10px;
        font-size: 1rem; font-weight: 700; color: #1a1d23;
    }
    .gnb-logo-icon {
        width: 32px; height: 32px; background: #1a56db;
        border-radius: 8px; display: flex; align-items: center;
        justify-content: center; font-size: 1rem; color: white;
    }
    .gnb-tag {
        font-size: 0.7rem; font-weight: 500; color: #6b7280;
        background: #f3f4f6; border-radius: 4px; padding: 2px 8px;
    }

    .main-wrap  { padding: 2rem 3rem; max-width: 1280px; margin: 0 auto; }
    .page-title { font-size: 1.5rem; font-weight: 700; color: #111827; letter-spacing: -0.03em; margin: 0 0 0.25rem 0; }
    .page-desc  { font-size: 0.85rem; color: #6b7280; margin: 0 0 2rem 0; }

    .input-panel {
        background: #ffffff; border: 1px solid #e5e7eb;
        border-radius: 12px; padding: 1.75rem 2rem; margin-bottom: 1.5rem;
    }
    .panel-label {
        font-size: 0.72rem; font-weight: 600; letter-spacing: 0.08em;
        text-transform: uppercase; color: #9ca3af; margin-bottom: 1rem;
    }
    .range-chip {
        display: inline-flex; align-items: center; gap: 8px;
        background: #eff6ff; border: 1px solid #bfdbfe;
        border-radius: 8px; padding: 8px 14px; margin-top: 0.6rem;
    }
    .range-chip-label { font-size: 0.72rem; font-weight: 600; color: #2563eb; text-transform: uppercase; letter-spacing: 0.06em; }
    .range-chip-value { font-family: 'IBM Plex Mono', monospace; font-size: 0.85rem; font-weight: 500; color: #1e40af; }

    .stButton > button {
        background: #1a56db !important; color: #ffffff !important;
        border: none !important; border-radius: 8px !important;
        font-family: 'Noto Sans KR', sans-serif !important;
        font-weight: 600 !important; font-size: 0.9rem !important;
        height: 48px !important;
        box-shadow: 0 1px 3px rgba(26,86,219,0.3) !important;
    }
    .stButton > button:hover { background: #1648c0 !important; }

    .kpi-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: 1rem; margin-bottom: 1.5rem; }
    .kpi-card {
        background: #ffffff; border: 1px solid #e5e7eb;
        border-radius: 10px; padding: 1.25rem 1.5rem;
        border-top: 3px solid transparent;
    }
    .kpi-card.blue   { border-top-color: #3b82f6; }
    .kpi-card.indigo { border-top-color: #6366f1; }
    .kpi-card.amber  { border-top-color: #f59e0b; }
    .kpi-card.green  { border-top-color: #10b981; }
    .kpi-card.red    { border-top-color: #ef4444; }
    .kpi-label { font-size: 0.72rem; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; color: #9ca3af; margin-bottom: 0.5rem; }
    .kpi-value { font-family: 'IBM Plex Mono', monospace; font-size: 1.65rem; font-weight: 600; color: #111827; line-height: 1.1; }
    .kpi-unit  { font-size: 0.85rem; color: #9ca3af; margin-left: 2px; }
    .kpi-sub   { font-size: 0.75rem; color: #d1d5db; margin-top: 0.3rem; }

    .verdict-box {
        border-radius: 12px; padding: 2rem 2.5rem;
        display: flex; align-items: center; gap: 2rem; margin-bottom: 1.5rem;
    }
    .verdict-box.pass { background: #f0fdf4; border: 1.5px solid #86efac; }
    .verdict-box.fail { background: #fef2f2; border: 1.5px solid #fca5a5; }
    .verdict-stamp {
        width: 72px; height: 72px; border-radius: 50%; flex-shrink: 0;
        display: flex; align-items: center; justify-content: center; font-size: 2rem;
    }
    .verdict-stamp.pass { background: #dcfce7; }
    .verdict-stamp.fail { background: #fee2e2; }
    .verdict-text  { flex: 1; }
    .verdict-title-pass { font-size: 1.4rem; font-weight: 700; color: #15803d; margin: 0 0 0.3rem 0; }
    .verdict-title-fail { font-size: 1.4rem; font-weight: 700; color: #b91c1c; margin: 0 0 0.3rem 0; }
    .verdict-detail { font-size: 0.88rem; color: #6b7280; margin: 0; line-height: 1.8; }
    .verdict-detail strong { color: #374151; }
    .verdict-meter { width: 130px; flex-shrink: 0; text-align: center; }
    .verdict-pct   { font-family: 'IBM Plex Mono', monospace; font-size: 2.2rem; font-weight: 600; line-height: 1; }
    .verdict-pct.pass { color: #16a34a; }
    .verdict-pct.fail { color: #dc2626; }
    .verdict-pct-lbl  { font-size: 0.72rem; color: #9ca3af; margin-top: 4px; }
    .prog-bg   { background: #e5e7eb; border-radius: 99px; height: 6px; margin-top: 10px; overflow: hidden; }
    .prog-pass { height: 100%; border-radius: 99px; background: #22c55e; }
    .prog-fail { height: 100%; border-radius: 99px; background: #ef4444; }

    .sec-label {
        font-size: 0.75rem; font-weight: 600; letter-spacing: 0.08em;
        text-transform: uppercase; color: #6b7280;
        border-bottom: 2px solid #e5e7eb;
        padding-bottom: 0.6rem; margin-bottom: 1rem;
    }

    [data-testid="stFileUploader"] {
        border: 1.5px dashed #d1d5db !important;
        border-radius: 8px !important; background: #f9fafb !important;
    }
    [data-testid="stFileUploader"]:hover {
        border-color: #3b82f6 !important; background: #eff6ff !important;
    }
    label, [data-testid="stWidgetLabel"] p {
        color: #374151 !important; font-size: 0.82rem !important; font-weight: 500 !important;
    }
    [data-testid="stDateInput"] input {
        border-radius: 8px !important; border-color: #d1d5db !important;
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 0.9rem !important; color: #111827 !important; background: #ffffff !important;
    }
    [data-testid="stDataFrame"] { border-radius: 8px !important; overflow: hidden !important; }
    [data-testid="stAlert"]     { border-radius: 8px !important; }
    [data-testid="stExpander"]  { border-radius: 8px !important; border: 1px solid #e5e7eb !important; }
    </style>
    """, unsafe_allow_html=True)


def render_gnb():
    st.markdown("""
    <div class="gnb">
        <div class="gnb-logo">
            <div class="gnb-logo-icon">🏗</div>
            감리실적 계산기
        </div>
        <span class="gnb-tag">전력기술관리법 기준</span>
    </div>
    """, unsafe_allow_html=True)


def render_page_title():
    st.markdown("""
    <div class="main-wrap">
    <h1 class="page-title">주택건설공사 감리영역 실적(연면적)계산</h1>
    <p class="page-desc">수행현황확인서 PDF를 업로드하면 입찰 기준(360,000 ㎡)에 따른 실적 면적을 자동 산출합니다.</p>
    """, unsafe_allow_html=True)


def render_kpi_cards(total_records: int, valid_count: int, field_count: int, total_area: float, is_pass: bool):
    area_color = "green" if is_pass else "red"
    st.markdown(f"""
    <div class="kpi-grid">
        <div class="kpi-card blue">
            <div class="kpi-label">총 추출 건수</div>
            <div class="kpi-value">{total_records}<span class="kpi-unit">건</span></div>
            <div class="kpi-sub">산업시설 제외 후</div>
        </div>
        <div class="kpi-card indigo">
            <div class="kpi-label">기간 내 유효 건수</div>
            <div class="kpi-value">{valid_count}<span class="kpi-unit">건</span></div>
            <div class="kpi-sub">3년 범위 중첩 기준</div>
        </div>
        <div class="kpi-card amber">
            <div class="kpi-label">참여 분야 수</div>
            <div class="kpi-value">{field_count}<span class="kpi-unit">개</span></div>
            <div class="kpi-sub">중복 제거</div>
        </div>
        <div class="kpi-card {area_color}">
            <div class="kpi-label">합계 면적</div>
            <div class="kpi-value">{total_area:,.0f}<span class="kpi-unit">㎡</span></div>
            <div class="kpi-sub">기준 {AREA_THRESHOLD:,} ㎡</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_verdict(verdict: dict, total_area: float):
    pct     = verdict["pct"]
    is_pass = verdict["pass"]
    cls     = "pass" if is_pass else "fail"
    icon    = "✅" if is_pass else "❌"
    title   = "입찰 참여 가능" if is_pass else "입찰 참여 불가능"
    title_cls = "verdict-title-pass" if is_pass else "verdict-title-fail"
    prog_cls  = "prog-pass" if is_pass else "prog-fail"

    if is_pass:
        detail = f"합계 <strong>{total_area:,.2f} ㎡</strong> ≥ 기준 <strong>{AREA_THRESHOLD:,} ㎡</strong><br>초과 면적: <strong>+{verdict['surplus']:,.2f} ㎡</strong>"
    else:
        detail = f"합계 <strong>{total_area:,.2f} ㎡</strong> &lt; 기준 <strong>{AREA_THRESHOLD:,} ㎡</strong><br>부족 면적: <strong>-{verdict['shortage']:,.2f} ㎡</strong>"

    st.markdown(f"""
    <div class="verdict-box {cls}">
        <div class="verdict-stamp {cls}">{icon}</div>
        <div class="verdict-text">
            <p class="{title_cls}">{title}</p>
            <p class="verdict-detail">{detail}</p>
        </div>
        <div class="verdict-meter">
            <div class="verdict-pct {cls}">{pct:.1f}<span style="font-size:1rem">%</span></div>
            <div class="verdict-pct-lbl">달성률</div>
            <div class="prog-bg"><div class="{prog_cls}" style="width:{pct:.1f}%"></div></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_section_label(label: str):
    st.markdown(f'<div class="sec-label">{label}</div>', unsafe_allow_html=True)

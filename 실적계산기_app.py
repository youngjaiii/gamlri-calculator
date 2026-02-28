import streamlit as st
import pdfplumber
import re
import pandas as pd
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

# ────────────────────────────────────────
# 설정
# ────────────────────────────────────────
AREA_THRESHOLD = 360_000
EXCLUDE_FIELDS = ["산업시설", "산업"]

# ────────────────────────────────────────
# 유틸 함수
# ────────────────────────────────────────
def parse_date(text: str):
    text = str(text).strip().replace(" ", "")
    patterns = [
        r"(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})",
        r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일",
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            try:
                return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                pass
    return None

def parse_number(text: str):
    text = re.sub(r"[,\s㎡m²]", "", str(text).strip())
    try:
        return float(text)
    except ValueError:
        return None

def overlap_days(s1, e1, s2, e2):
    return max((min(e1, e2) - max(s1, s2)).days + 1, 0)

def extract_records(uploaded_file):
    records = []
    warnings = []

    with pdfplumber.open(uploaded_file) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            tables = page.extract_tables()
            for table in tables:
                if not table:
                    continue

                header_row_idx = None
                headers = []
                for i, row in enumerate(table):
                    row_text = " ".join(str(c) for c in row if c)
                    if any(kw in row_text for kw in ["연면적", "공사명", "감리기간", "이행비율", "분야"]):
                        header_row_idx = i
                        headers = [str(c).strip().replace("\n", "") if c else "" for c in row]
                        break

                if header_row_idx is None:
                    continue

                col_map = {}
                for idx, h in enumerate(headers):
                    h_clean = h.replace(" ", "")
                    if "분야" in h_clean or "공사종류" in h_clean:
                        col_map["분야"] = idx
                    elif "연면적" in h_clean:
                        col_map["연면적"] = idx
                    elif "이행비율" in h_clean or "이행율" in h_clean:
                        col_map["이행비율"] = idx
                    elif "착공" in h_clean or "시작" in h_clean or "개시" in h_clean:
                        col_map["시작일"] = idx
                    elif "준공" in h_clean or "종료" in h_clean or "완료" in h_clean:
                        col_map["종료일"] = idx
                    elif "감리기간" in h_clean:
                        col_map["감리기간"] = idx

                if "연면적" not in col_map:
                    warnings.append(f"⚠️ {page_num}페이지: 필수 컬럼(연면적) 없음 → 헤더: {headers}")
                    continue

                for row in table[header_row_idx + 1:]:
                    if not any(row):
                        continue

                    def get(col_name):
                        idx = col_map.get(col_name)
                        return str(row[idx]).strip() if idx is not None and row[idx] else ""

                    field_text = get("분야")
                    if any(ex in field_text for ex in EXCLUDE_FIELDS):
                        continue

                    area = parse_number(get("연면적"))
                    if area is None or area <= 0:
                        continue

                    rate_text = get("이행비율").replace("%", "").strip()
                    rate = parse_number(rate_text)
                    rate = 100.0 if rate is None else rate
                    rate_ratio = rate / 100.0 if rate > 1 else rate

                    start_date = end_date = None
                    if "감리기간" in col_map:
                        dates = re.findall(r"\d{4}[.\-/년]\d{1,2}[.\-/월]\d{1,2}일?", get("감리기간"))
                        if len(dates) >= 2:
                            start_date = parse_date(dates[0])
                            end_date = parse_date(dates[1])
                    else:
                        start_date = parse_date(get("시작일"))
                        end_date = parse_date(get("종료일"))

                    if start_date is None or end_date is None:
                        warnings.append(f"⚠️ 날짜 파싱 실패: {row}")
                        continue

                    records.append({
                        "분야": field_text,
                        "연면적(㎡)": area,
                        "이행비율": rate_ratio,
                        "시작일": start_date,
                        "종료일": end_date,
                    })

    return records, warnings

def calculate(records, d_start, d_end):
    rows = []
    total = 0.0
    for r in records:
        total_days = (r["종료일"] - r["시작일"]).days + 1
        if total_days <= 0:
            continue
        ol = overlap_days(r["시작일"], r["종료일"], d_start, d_end)
        if ol <= 0:
            continue
        contribution = r["연면적(㎡)"] * r["이행비율"] * (ol / total_days)
        total += contribution
        rows.append({
            "분야": r["분야"],
            "연면적(㎡)": f"{r['연면적(㎡)']:,.0f}",
            "이행비율": f"{r['이행비율']:.0%}",
            "감리기간": f"{r['시작일']} ~ {r['종료일']}",
            "중첩일수": ol,
            "전체일수": total_days,
            "기여면적(㎡)": f"{contribution:,.2f}",
        })
    return rows, total

# ────────────────────────────────────────
# 화면 구성
# ────────────────────────────────────────
st.set_page_config(page_title="감리실적 계산기", page_icon="🏗️", layout="centered")

st.title("🏗️ 공사감리 실적 계산기")
st.caption("공사감리용역수행현황확인서 PDF를 업로드하면 자동으로 실적을 계산합니다.")

st.divider()

# ── 입력 영역 ──
col1, col2 = st.columns([1, 1])
with col1:
    bid_date = st.date_input("📅 입찰 공고일", value=date.today(), format="YYYY.MM.DD")
with col2:
    uploaded_file = st.file_uploader("📄 PDF 파일 업로드", type=["pdf"])

# 기준 범위 표시
d_end = bid_date - timedelta(days=1)
d_start = bid_date - relativedelta(years=3)
st.info(f"📌 기준 범위: **{d_start}** ~ **{d_end}**")

st.divider()

# ── 계산 버튼 ──
if st.button("🔍 실적 계산하기", type="primary", use_container_width=True):
    if uploaded_file is None:
        st.error("PDF 파일을 먼저 업로드해 주세요.")
    else:
        with st.spinner("PDF 분석 중..."):
            records, warnings = extract_records(uploaded_file)

        # 경고 표시
        if warnings:
            with st.expander(f"⚠️ 파싱 경고 {len(warnings)}건 (클릭하여 확인)"):
                for w in warnings:
                    st.text(w)

        if not records:
            st.error("유효한 데이터를 찾지 못했습니다. PDF 표 구조를 확인해 주세요.")
        else:
            st.success(f"✅ 유효 레코드 {len(records)}건 추출 완료 (산업시설 제외)")

            # 상세 결과 표
            result_rows, total_area = calculate(records, d_start, d_end)

            st.subheader("📋 상세 계산 결과")
            if result_rows:
                df = pd.DataFrame(result_rows)
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.warning("기준 기간과 중첩되는 실적이 없습니다.")

            st.divider()

            # 최종 판정
            st.subheader("🏁 최종 판정")
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("합계 면적", f"{total_area:,.2f} ㎡")
            with col_b:
                st.metric("기준 면적", f"{AREA_THRESHOLD:,} ㎡")

            if total_area >= AREA_THRESHOLD:
                st.success(f"## ✅ 기준 충족！{total_area:,.2f}㎡ ≥ 360,000㎡")
                st.balloons()
            else:
                shortage = AREA_THRESHOLD - total_area
                st.error(f"## ❌ 기준 미달  |  부족분: {shortage:,.2f} ㎡")
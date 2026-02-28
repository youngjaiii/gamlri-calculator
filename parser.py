"""
parser.py
PDF에서 감리 실적 데이터를 추출하는 모듈
"""
import re
import pdfplumber
from datetime import date

EXCLUDE_FIELDS = ["산업시설", "산업"]


def parse_date(text: str) -> date | None:
    text = str(text).strip().replace(" ", "")
    for pattern in [
        r"(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})",
        r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일",
    ]:
        m = re.search(pattern, text)
        if m:
            try:
                return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                pass
    return None


def parse_number(text: str) -> float | None:
    text = re.sub(r"[,\s㎡m²]", "", str(text).strip())
    try:
        return float(text)
    except ValueError:
        return None


def extract_dates_from_cell(text: str) -> tuple[date | None, date | None]:
    """
    감리기간 셀 하나에서 시작일·종료일 추출
    예: '2023.12.19\n2025.06.30\n(560일)'
    """
    date_strings = re.findall(r"\d{4}[.\-/]\d{1,2}[.\-/]\d{1,2}", str(text))
    parsed = [d for d in (parse_date(s) for s in date_strings) if d]
    return (parsed[0], parsed[1]) if len(parsed) >= 2 else (None, None)


def _build_col_map(headers: list[str]) -> dict:
    col_map = {}
    for idx, h in enumerate(headers):
        hc = h.replace(" ", "")
        if any(k in hc for k in ["비고참여분야", "참여분야", "분야", "공사종류"]):
            col_map["분야"] = idx
        elif "연면적" in hc:
            col_map["연면적"] = idx
        elif "이행비율" in hc or "이행율" in hc:
            col_map["이행비율"] = idx
        elif "감리기간" in hc:
            col_map["감리기간"] = idx
        elif any(k in hc for k in ["착공", "시작", "개시"]):
            col_map["시작일"] = idx
        elif any(k in hc for k in ["준공", "종료", "완료"]):
            col_map["종료일"] = idx
    return col_map


def _parse_row(row: list, col_map: dict) -> dict | None:
    def get(key):
        i = col_map.get(key)
        return str(row[i]).strip() if i is not None and row[i] else ""

    # 산업시설 제외
    field_text = get("분야")
    if any(ex in field_text for ex in EXCLUDE_FIELDS):
        return None

    # 연면적
    area = parse_number(get("연면적"))
    if area is None or area <= 0:
        return None

    # 이행비율 (없으면 100%)
    rate_raw = parse_number(get("이행비율").replace("%", "").strip())
    rate_val = 100.0 if rate_raw is None else rate_raw
    rate_ratio = rate_val / 100.0 if rate_val > 1 else rate_val

    # 감리 기간
    start_date = end_date = None
    if "감리기간" in col_map:
        start_date, end_date = extract_dates_from_cell(get("감리기간"))
    if start_date is None and "시작일" in col_map:
        start_date = parse_date(get("시작일"))
    if end_date is None and "종료일" in col_map:
        end_date = parse_date(get("종료일"))

    if not start_date or not end_date:
        return None

    return {
        "분야":     field_text,
        "연면적":   area,
        "이행비율": rate_ratio,
        "시작일":   start_date,
        "종료일":   end_date,
    }


def extract_records(uploaded_file) -> tuple[list[dict], list[str]]:
    records: list[dict] = []
    warnings: list[str] = []

    with pdfplumber.open(uploaded_file) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            for table in (page.extract_tables() or []):
                if not table:
                    continue

                # 헤더 행 탐색
                header_row_idx = None
                headers = []
                for i, row in enumerate(table):
                    row_text = " ".join(str(c) for c in row if c)
                    if any(kw in row_text for kw in ["연면적", "감리기간", "이행비율", "참여분야"]):
                        header_row_idx = i
                        headers = [str(c).strip().replace("\n", " ") if c else "" for c in row]
                        break

                if header_row_idx is None:
                    continue

                col_map = _build_col_map(headers)

                if "연면적" not in col_map:
                    warnings.append(f"⚠️ {page_num}페이지: 연면적 컬럼 없음 → 헤더: {headers}")
                    continue

                for row in table[header_row_idx + 1:]:
                    if not any(row):
                        continue
                    record = _parse_row(row, col_map)
                    if record:
                        records.append(record)
                    else:
                        # 유효한 행인데 날짜만 실패한 경우 경고
                        def get(key):
                            i = col_map.get(key)
                            return str(row[i]).strip() if i is not None and row[i] else ""
                        area = parse_number(get("연면적"))
                        field = get("분야")
                        if area and area > 0 and not any(ex in field for ex in EXCLUDE_FIELDS):
                            warnings.append(f"⚠️ 날짜 파싱 실패: {[str(c) for c in row]}")

    return records, warnings

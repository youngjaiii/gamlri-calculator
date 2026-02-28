"""
parser.py
PDF에서 감리 실적 데이터를 추출하는 모듈
연면적 모드 / 용역비 모드 공통으로 사용
"""
import re
import pdfplumber
from datetime import date

# 제외할 분야 키워드
EXCLUDE_FIELDS = ["산업시설", "산업"]


def parse_date(text: str) -> date | None:
    """다양한 날짜 형식 → date 객체 변환"""
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
    """쉼표·단위 제거 후 숫자 변환"""
    text = re.sub(r"[,\s㎡m²천원]", "", str(text).strip())
    try:
        return float(text)
    except ValueError:
        return None


def extract_dates_from_cell(text: str) -> tuple[date | None, date | None]:
    """
    감리기간 셀에서 시작일·종료일 추출
    예: '2023.12.19\n2025.06.30\n(560일)'
    """
    date_strings = re.findall(r"\d{4}[.\-/]\d{1,2}[.\-/]\d{1,2}", str(text))
    parsed = [d for d in (parse_date(s) for s in date_strings) if d]
    return (parsed[0], parsed[1]) if len(parsed) >= 2 else (None, None)


def _build_col_map(headers: list[str]) -> dict:
    """헤더 목록 → 컬럼명:인덱스 딕셔너리"""
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
        elif any(k in hc for k in ["용역명", "공사명", "용역명칭"]):
            col_map["용역명"] = idx
        elif any(k in hc for k in ["용역비", "계약금액"]):
            # '연면적' 컬럼이 아닌 경우에만 용역비로 매핑
            if "연면적" not in hc:
                col_map["용역비"] = idx
    return col_map


def _parse_row(row: list, col_map: dict) -> dict | None:
    """행 하나를 파싱해 레코드 반환, 유효하지 않으면 None"""
    def get(key):
        i = col_map.get(key)
        return str(row[i]).strip() if i is not None and row[i] else ""

    # 산업시설 제외
    field_text = get("분야")
    if any(ex in field_text for ex in EXCLUDE_FIELDS):
        return None

    # 연면적 (없어도 허용 - 용역비 모드에서 사용)
    area = parse_number(get("연면적"))

    # 이행비율 (없으면 100% 기본값)
    rate_raw = parse_number(get("이행비율").replace("%", "").strip())
    rate_val = 100.0 if rate_raw is None else rate_raw
    rate_ratio = rate_val / 100.0 if rate_val > 1 else rate_val

    # 용역비 (없어도 허용 - 연면적 모드에서 사용)
    fee = parse_number(get("용역비"))

    # 용역명
    name = get("용역명") or "—"

    # 감리 기간
    start_date = end_date = None
    if "감리기간" in col_map:
        start_date, end_date = extract_dates_from_cell(get("감리기간"))
    if start_date is None and "시작일" in col_map:
        start_date = parse_date(get("시작일"))
    if end_date is None and "종료일" in col_map:
        end_date = parse_date(get("종료일"))

    # 날짜 없으면 제외
    if not start_date or not end_date:
        return None

    # 연면적도 없고 용역비도 없으면 제외
    if area is None and fee is None:
        return None

    return {
        "용역명":   name,
        "분야":     field_text,
        "연면적":   area,       # None 가능 (연면적 없는 경우)
        "이행비율": rate_ratio,
        "용역비":   fee,        # None 가능 (용역비 없는 경우)
        "시작일":   start_date,
        "종료일":   end_date,
    }


def extract_records(uploaded_file) -> tuple[list[dict], list[str]]:
    """
    PDF에서 완료·진행 중 용역 전체를 추출

    Returns:
        records  : 파싱된 레코드 리스트
        warnings : 파싱 경고 메시지 리스트
    """
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
                    if any(kw in row_text for kw in ["연면적", "감리기간", "이행비율", "참여분야", "용역비"]):
                        header_row_idx = i
                        headers = [str(c).strip().replace("\n", " ") if c else "" for c in row]
                        break

                if header_row_idx is None:
                    continue

                col_map = _build_col_map(headers)

                # 날짜 컬럼이 하나도 없으면 skip
                has_date = "감리기간" in col_map or ("시작일" in col_map and "종료일" in col_map)
                if not has_date:
                    warnings.append(f"⚠️ {page_num}페이지: 날짜 컬럼 없음 → 헤더: {headers}")
                    continue

                for row in table[header_row_idx + 1:]:
                    if not any(row):
                        continue

                    record = _parse_row(row, col_map)
                    if record:
                        records.append(record)
                    else:
                        # 유효해 보이지만 실패한 행만 경고
                        def get(key):
                            i = col_map.get(key)
                            return str(row[i]).strip() if i is not None and row[i] else ""
                        field = get("분야")
                        if not any(ex in field for ex in EXCLUDE_FIELDS):
                            raw = [str(c) for c in row if c]
                            if raw:
                                warnings.append(f"⚠️ {page_num}p 파싱 실패: {raw}")

    return records, warnings

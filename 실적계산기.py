import pdfplumber
import re
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

# ※ dateutil 설치 필요: pip install python-dateutil

# ─────────────────────────────────────────
# [설정] PDF 파일 경로를 여기에 입력하세요
PDF_PATH = "용역현황확인서.pdf"   # ← PDF 파일명을 맞게 수정
# ─────────────────────────────────────────

AREA_THRESHOLD = 360_000  # 판정 기준 (㎡)

# 제외 분야 키워드
EXCLUDE_FIELDS = ["산업시설", "산업"]


def parse_date(text: str) -> date | None:
    """'YYYY.MM.DD', 'YYYY-MM-DD', 'YYYY년MM월DD일' 등 다양한 형식 파싱"""
    text = text.strip().replace(" ", "")
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


def parse_number(text: str) -> float | None:
    """숫자 문자열에서 쉼표·공백 제거 후 float 변환"""
    text = re.sub(r"[,\s㎡m²]", "", text.strip())
    try:
        return float(text)
    except ValueError:
        return None


def overlap_days(start1: date, end1: date, start2: date, end2: date) -> int:
    """두 기간의 중첩 일수 계산"""
    overlap_start = max(start1, start2)
    overlap_end = min(end1, end2)
    delta = (overlap_end - overlap_start).days + 1
    return max(delta, 0)


def extract_records(pdf_path: str) -> list[dict]:
    """PDF에서 표 데이터를 추출하여 레코드 리스트로 반환"""
    records = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            tables = page.extract_tables()
            for table in tables:
                if not table:
                    continue

                # 헤더 행 찾기 (컬럼명 자동 감지)
                header_row_idx = None
                headers = []
                for i, row in enumerate(table):
                    row_text = " ".join(str(c) for c in row if c)
                    # 일반적인 헤더 키워드
                    if any(kw in row_text for kw in ["연면적", "공사명", "감리기간", "이행비율", "분야"]):
                        header_row_idx = i
                        headers = [str(c).strip().replace("\n", "") if c else "" for c in row]
                        break

                if header_row_idx is None:
                    continue

                # 컬럼 인덱스 매핑 (유사 키워드로 유연하게 탐색)
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
                        col_map["감리기간"] = idx  # "YYYY.MM.DD ~ YYYY.MM.DD" 형태

                required = {"연면적"}
                if not required.issubset(col_map.keys()):
                    print(f"  [경고] {page_num}페이지 표에서 필수 컬럼을 찾지 못했습니다. (발견된 헤더: {headers})")
                    continue

                # 데이터 행 파싱
                for row in table[header_row_idx + 1:]:
                    if not any(row):
                        continue

                    def get(col_name):
                        idx = col_map.get(col_name)
                        return str(row[idx]).strip() if idx is not None and row[idx] else ""

                    # 분야 확인 (산업시설 제외)
                    field_text = get("분야")
                    if any(ex in field_text for ex in EXCLUDE_FIELDS):
                        continue

                    # 연면적 파싱
                    area_text = get("연면적")
                    area = parse_number(area_text)
                    if area is None or area <= 0:
                        continue

                    # 이행비율 파싱 (기본값 100%)
                    rate_text = get("이행비율")
                    rate_clean = rate_text.replace("%", "").strip()
                    rate = parse_number(rate_clean)
                    if rate is None:
                        rate = 100.0
                    # 100 초과이면 이미 소수점 표기 (예: 1.0 → 100%)
                    rate_ratio = rate / 100.0 if rate > 1 else rate

                    # 감리 기간 파싱
                    start_date = end_date = None

                    if "감리기간" in col_map:
                        period_text = get("감리기간")
                        dates = re.findall(r"\d{4}[.\-/년]\d{1,2}[.\-/월]\d{1,2}일?", period_text)
                        if len(dates) >= 2:
                            start_date = parse_date(dates[0])
                            end_date = parse_date(dates[1])
                    else:
                        start_date = parse_date(get("시작일"))
                        end_date = parse_date(get("종료일"))

                    if start_date is None or end_date is None:
                        print(f"  [경고] 날짜 파싱 실패 → 행 건너뜀: {row}")
                        continue

                    records.append({
                        "분야": field_text,
                        "연면적": area,
                        "이행비율": rate_ratio,
                        "시작일": start_date,
                        "종료일": end_date,
                    })

    return records


def calculate(records: list[dict], d_start: date, d_end: date) -> float:
    """핵심 공식 적용 후 합계 반환"""
    total = 0.0
    print("\n" + "=" * 70)
    print(f"{'분야':<12} {'연면적':>10} {'이행비율':>8} {'감리기간':<25} {'중첩일':>6} {'전체일':>6} {'기여면적':>12}")
    print("-" * 70)

    for r in records:
        total_days = (r["종료일"] - r["시작일"]).days + 1
        if total_days <= 0:
            continue

        ol = overlap_days(r["시작일"], r["종료일"], d_start, d_end)
        if ol <= 0:
            continue  # 3년 범위와 겹치지 않으면 제외

        contribution = r["연면적"] * r["이행비율"] * (ol / total_days)
        total += contribution

        print(
            f"{r['분야']:<12} "
            f"{r['연면적']:>10,.0f} "
            f"{r['이행비율']:>7.1%} "
            f"{str(r['시작일'])} ~ {str(r['종료일'])}  "
            f"{ol:>6} "
            f"{total_days:>6} "
            f"{contribution:>12,.2f}"
        )

    print("=" * 70)
    return total


def main():
    # ── 1. 입찰 공고일 입력 ──────────────────────────────────────
    print("=" * 50)
    print("  공사감리 실적 계산기")
    print("=" * 50)
    raw = input("\n입찰 공고일을 입력하세요 (예: 2025.03.15): ").strip()
    T = parse_date(raw)
    if T is None:
        print("❌ 날짜 형식을 인식하지 못했습니다. 다시 실행해 주세요.")
        return

    D_end = T - timedelta(days=1)           # 어제 (공고일 전날)
    D_start = T - relativedelta(years=3)    # 정확히 3년 전

    print(f"\n▶ 공고일  : {T}")
    print(f"▶ 기준 범위: {D_start}  ~  {D_end}")

    # ── 2. PDF 파싱 ──────────────────────────────────────────────
    print(f"\n📄 PDF 파일 읽는 중: {PDF_PATH}")
    try:
        records = extract_records(PDF_PATH)
    except FileNotFoundError:
        print(f"❌ PDF 파일을 찾을 수 없습니다: {PDF_PATH}")
        print("   ▷ 코드 상단 PDF_PATH 변수를 파일 경로에 맞게 수정해 주세요.")
        return

    print(f"✅ 유효 레코드 수: {len(records)}건 (산업시설·연면적 없음 제외 후)")

    if not records:
        print("❌ 처리할 데이터가 없습니다.")
        return

    # ── 3. 계산 ─────────────────────────────────────────────────
    total_area = calculate(records, D_start, D_end)

    # ── 4. 최종 판정 ─────────────────────────────────────────────
    print(f"\n📊 최종 합계 면적 : {total_area:>15,.2f} ㎡")
    print(f"   기준 면적      : {AREA_THRESHOLD:>15,.0f} ㎡")
    print()
    if total_area >= AREA_THRESHOLD:
        print("✅ 판정: 기준 충족 (360,000㎡ 이상)")
    else:
        shortage = AREA_THRESHOLD - total_area
        print(f"❌ 판정: 기준 미달 (부족분: {shortage:,.2f} ㎡)")


if __name__ == "__main__":
    main()
"""
calculator.py
감리 실적 면적 계산 로직 모듈
"""
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

AREA_THRESHOLD = 360_000  # 판정 기준 (㎡)


def get_base_period(bid_date: date) -> tuple[date, date]:
    """공고일 기준 실적 인정 기간 반환 (3년 전 ~ 전날)"""
    return bid_date - relativedelta(years=3), bid_date - timedelta(days=1)


def _overlap_days(s1: date, e1: date, s2: date, e2: date) -> int:
    return max((min(e1, e2) - max(s1, s2)).days + 1, 0)


def calculate_total(
    records: list[dict],
    d_start: date,
    d_end: date,
) -> tuple[list[dict], float]:
    """
    공식: 연면적 × 이행비율 × (중첩일수 / 전체감리일수)
    Returns: (표시용 행 리스트, 합계 면적)
    """
    result_rows: list[dict] = []
    total_area = 0.0

    for r in records:
        total_days = (r["종료일"] - r["시작일"]).days + 1
        if total_days <= 0:
            continue
        ol = _overlap_days(r["시작일"], r["종료일"], d_start, d_end)
        if ol <= 0:
            continue

        contribution = r["연면적"] * r["이행비율"] * (ol / total_days)
        total_area += contribution

        result_rows.append({
            "분야":         r["분야"],
            "연면적(㎡)":   f"{r['연면적']:,.0f}",
            "이행비율":     f"{r['이행비율']:.0%}",
            "감리 시작일":  str(r["시작일"]),
            "감리 종료일":  str(r["종료일"]),
            "중첩일수":     ol,
            "전체일수":     total_days,
            "기여면적(㎡)": round(contribution, 2),
        })

    return result_rows, total_area


def get_verdict(total_area: float) -> dict:
    """판정 결과 반환"""
    is_pass = total_area >= AREA_THRESHOLD
    return {
        "pass":     is_pass,
        "pct":      min(total_area / AREA_THRESHOLD * 100, 100),
        "surplus":  total_area - AREA_THRESHOLD if is_pass else 0.0,
        "shortage": AREA_THRESHOLD - total_area if not is_pass else 0.0,
    }

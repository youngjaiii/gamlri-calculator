"""
calculator.py
연면적 계산 / 용역비 계산 로직 모듈

[중요] 두 모드의 계산 공식 차이
- 연면적 모드: 환산면적   = 연면적 × 이행비율 × W
  → PDF 표에 연면적은 이행비율이 반영되지 않은 수치이므로 직접 곱해야 함
- 용역비 모드: 환산용역비 = 용역비 × W
  → PDF 표에 용역비는 이미 이행비율이 반영된 수치이므로 추가로 곱하지 않음
"""
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta


def get_base_period(bid_date: date) -> tuple[date, date]:
    """
    입찰 공고일 기준 실적 인정 기간 반환
    - 시작(d_start): 공고일 기준 정확히 3년 전
    - 종료(d_end)  : 공고일 전날
    """
    d_start = bid_date - relativedelta(years=3)
    d_end   = bid_date - timedelta(days=1)
    return d_start, d_end


def _overlap_days(s1: date, e1: date, s2: date, e2: date) -> int:
    """
    두 기간의 중첩 일수 계산 (시작일·종료일 모두 포함)
    중첩 없으면 0 반환
    """
    return max((min(e1, e2) - max(s1, s2)).days + 1, 0)


def _calc_weight(record: dict, d_start: date, d_end: date) -> tuple[float, int, int]:
    """
    가중치 W = 인정범위 내 중첩일수 / 전체 감리기간

    Returns:
        weight     : 가중치 (0.0 ~ 1.0)
        ol         : 중첩 일수
        total_days : 전체 감리 일수
    """
    total_days = (record["종료일"] - record["시작일"]).days + 1
    if total_days <= 0:
        return 0.0, 0, total_days
    ol = _overlap_days(record["시작일"], record["종료일"], d_start, d_end)
    weight = ol / total_days if ol > 0 else 0.0
    return weight, ol, total_days


def _get_verdict(total: float, goal: float) -> dict:
    """목표 대비 달성 여부 반환"""
    is_pass = total >= goal
    pct     = min(total / goal * 100, 100) if goal > 0 else 0.0
    return {
        "pass":     is_pass,
        "pct":      pct,
        "surplus":  total - goal if is_pass else 0.0,
        "shortage": goal - total if not is_pass else 0.0,
        "goal":     goal,
    }


def calculate_area(
    records: list[dict],
    d_start: date,
    d_end: date,
    goal: float,
) -> tuple[list[dict], float, dict]:
    """
    [연면적 모드]
    공식: 환산면적 = 연면적 × 이행비율 × W
    - 연면적이 없는 항목 제외
    - 3년 범위와 중첩 없는 항목 제외
    """
    result_rows: list[dict] = []
    total = 0.0

    for r in records:
        if r["연면적"] is None:
            continue  # 연면적 없으면 제외

        weight, ol, total_days = _calc_weight(r, d_start, d_end)
        if ol <= 0:
            continue  # 기간 중첩 없으면 제외

        # 이행비율 반영 (연면적에는 이행비율이 미반영)
        converted = r["연면적"] * r["이행비율"] * weight
        total += converted

        result_rows.append({
            "용역명":       r["용역명"],
            "분야":         r["분야"],
            "연면적(㎡)":   f"{r['연면적']:,.0f}",
            "이행비율":     f"{r['이행비율']:.0%}",
            "감리 시작일":  str(r["시작일"]),
            "감리 종료일":  str(r["종료일"]),
            "중첩일수":     ol,
            "전체일수":     total_days,
            "환산면적(㎡)": round(converted, 2),
        })

    return result_rows, total, _get_verdict(total, goal)


def calculate_fee(
    records: list[dict],
    d_start: date,
    d_end: date,
    goal: float,
) -> tuple[list[dict], float, dict]:
    """
    [용역비 모드]
    공식: 환산용역비 = 용역비 × W
    - 용역비에는 이행비율을 곱하지 않음
      (PDF 표의 용역비는 이미 이행비율이 반영된 수치)
    - 용역비가 없는 항목 제외
    - 3년 범위와 중첩 없는 항목 제외
    """
    result_rows: list[dict] = []
    total = 0.0

    for r in records:
        if r["용역비"] is None:
            continue  # 용역비 없으면 제외

        weight, ol, total_days = _calc_weight(r, d_start, d_end)
        if ol <= 0:
            continue  # 기간 중첩 없으면 제외

        # 이행비율 미반영 (용역비에는 이미 반영됨)
        converted = r["용역비"] * weight
        total += converted

        result_rows.append({
            "용역명":           r["용역명"],
            "분야":             r["분야"],
            "용역비(천원)":     f"{r['용역비']:,.0f}",
            "감리 시작일":      str(r["시작일"]),
            "감리 종료일":      str(r["종료일"]),
            "중첩일수":         ol,
            "전체일수":         total_days,
            "환산용역비(천원)": round(converted, 2),
        })

    return result_rows, total, _get_verdict(total, goal)

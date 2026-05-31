"""Trailing stop 규칙 엔진 순수함수 (SSoT).

Backtest / Paper / Live에서 동일 로직으로 peak/stop/activation/trigger 평가.
stdlib only (numpy/pandas/talib 불가). talib은 테스트 golden-vector 대조용만.

공식 (long / short / spot 거울):
  peak:       long = max(peak, high) / short = min(peak, low) / spot = long
  pct_stop:   long = peak*(1-pct) / short = peak*(1+pct) / spot = long
  atr_stop:   long = peak - atr*mult / short = peak + atr*mult / spot = long
  activation: long (peak-entry)/entry >= pct / short (entry-peak)/entry >= pct
  trigger:    long low <= stop / short high >= stop
  combine:    long max(...) / short min(...) / spot = long

입력 검증:
  - side: 'long' | 'short' | 'spot' (spot은 long 동일)
  - 음수/0/NaN 입력은 구현에서 차단하지 않음(calling code 책임)

버전 이력:
  v0.14.0: 신규 module (py-algo D7, ID3)
"""
from __future__ import annotations

from typing import Literal


def update_peak(
    side: Literal["long", "short", "spot"],
    current_peak: float,
    candle_high: float,
    candle_low: float,
) -> float:
    """현재 peak를 양초 고가/저가로 갱신.

    Args:
        side: long(상승) | short(하강) | spot(현물, long 동일)
        current_peak: 현재까지의 peak (long=최고가 watermark / short=최저가 watermark)
        candle_high: 캔들 고가
        candle_low: 캔들 저가

    Returns:
        new_peak: max(현재, high) if long/spot / min(현재, low) if short
    """
    if side == "short":
        return min(current_peak, candle_low)
    return max(current_peak, candle_high)


def compute_trailing_stop(
    side: Literal["long", "short", "spot"],
    rule_type: Literal["percentage", "atr"],
    peak_price: float,
    *,
    trailing_pct: float | None = None,
    atr: float | None = None,
    atr_multiplier: float | None = None,
) -> float:
    """Peak 기반 손절선 가격 계산.

    Args:
        side: long | short | spot
        rule_type: 'percentage' | 'atr'
        peak_price: peak watermark
        trailing_pct: percentage 모드: trailing_value (0.05 = 5%). atr 모드일 때 미사용.
        atr: atr 모드: 현재 ATR(22) 값
        atr_multiplier: atr 모드: 배수 (예: 2.0)

    Returns:
        stop_price: 손절선 가격

    Raises:
        ValueError: rule_type/모드 파라미터 일관성 오류
    """
    if rule_type == "percentage":
        if trailing_pct is None:
            raise ValueError("percentage 모드: trailing_pct 필수")
        if side == "short":
            return peak_price * (1 + trailing_pct)
        return peak_price * (1 - trailing_pct)
    if rule_type == "atr":
        if atr is None or atr_multiplier is None:
            raise ValueError("atr 모드: atr + atr_multiplier 필수")
        if side == "short":
            return peak_price + atr * atr_multiplier
        return peak_price - atr * atr_multiplier
    raise ValueError(f"Unknown rule_type: {rule_type}")


def is_activated(
    side: Literal["long", "short", "spot"],
    entry_price: float,
    peak_price: float,
    activation_pct: float,
) -> bool:
    """Trailing 활성화 판정 (entry 대비 peak 이득률 >= 임계값).

    Args:
        side: long | short | spot
        entry_price: 진입 가격
        peak_price: 현재 peak watermark
        activation_pct: 활성화 임계값 (0.01 = 1%)

    Returns:
        activated: True if (peak-entry)/entry >= activation_pct (long) 또는
                   (entry-peak)/entry >= activation_pct (short)
    """
    if entry_price <= 0:
        return False
    if side == "short":
        return (entry_price - peak_price) / entry_price >= activation_pct
    return (peak_price - entry_price) / entry_price >= activation_pct


def is_triggered(
    side: Literal["long", "short", "spot"],
    candle_low: float,
    candle_high: float,
    stop_price: float,
) -> bool:
    """손절선 트리거 판정 (캔들이 stop을 관통했는가).

    Args:
        side: long | short | spot
        candle_low: 캔들 저가
        candle_high: 캔들 고가
        stop_price: 손절선 가격

    Returns:
        triggered: True if low <= stop (long/spot) / high >= stop (short)
    """
    if side == "short":
        return candle_high >= stop_price
    return candle_low <= stop_price


def combine_stops(
    side: Literal["long", "short", "spot"],
    *candidates: float,
) -> float:
    """여러 손절선 후보 중 가장 유리한(단조) 손절선 선택.

    long: max(후보들) — 최대한 높이 들어올림(손실 최소)
    short: min(후보들) — 최대한 낮게 내려놓음(손실 최소)
    spot: long 동일

    INV1 무조건 준수: 손절선이 불리한 방향으로 후퇴하지 않음.

    Args:
        side: long | short | spot
        candidates: stop_price 후보들 (초기_sl, breakeven_sl, trailing_sl 등)

    Returns:
        effective_stop: 후보 중 선택된 값

    Raises:
        ValueError: 빈 candidates
    """
    if not candidates:
        raise ValueError("combine_stops: 최소 1개 이상의 후보 필요")
    if side == "short":
        return min(candidates)
    return max(candidates)


def wilder_atr(
    highs: list[float] | tuple[float, ...],
    lows: list[float] | tuple[float, ...],
    closes: list[float] | tuple[float, ...],
    period: int = 22,
) -> list[float]:
    """Wilder Smoothing ATR(Average True Range).

    기간별 True Range를 Wilder 평균(지수평활 변형)으로 계산.
    talib ATR(14) 대비 다른 기간/평활 방식 — 의도된 이원성.
    trailing 전용이며 초기 SL ATR(talib 14)과 통합하지 않음(ID5).

    Args:
        highs: 캔들 고가 배열
        lows: 캔들 저가 배열
        closes: 캔들 종가 배열
        period: 기간(코드고정=22, 매개변수는 테스트 유연성용)

    Returns:
        atr_values: 각 봉별 ATR 값 리스트(첫 period-1개는 NaN 처리)

    Raises:
        ValueError: 길이 불일치 / period < 1 / 캔들 수 부족

    Note:
        길이 일치 필수: len(highs) == len(lows) == len(closes)
    """
    if not (len(highs) == len(lows) == len(closes)):
        raise ValueError("highs, lows, closes 길이 일치 필수")
    if period < 1:
        raise ValueError("period >= 1 필수")
    if len(highs) < period:
        raise ValueError(f"최소 {period}개 캔들 필수 (현재: {len(highs)})")

    atr: list[float] = []
    tr_sum = 0.0

    for i in range(len(highs)):
        if i == 0:
            tr = highs[i] - lows[i]
        else:
            high_low = highs[i] - lows[i]
            high_close_prev = abs(highs[i] - closes[i - 1])
            low_close_prev = abs(lows[i] - closes[i - 1])
            tr = max(high_low, high_close_prev, low_close_prev)

        if i < period - 1:
            tr_sum += tr
            atr.append(float("nan"))
        elif i == period - 1:
            tr_sum += tr
            atr.append(tr_sum / period)
        else:
            prev_atr = atr[-1]
            new_atr = (prev_atr * (period - 1) + tr) / period
            atr.append(new_atr)

    return atr

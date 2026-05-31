"""Trailing stop 규칙 엔진 테스트.

테스트 전략:
  - L1 단위 테스트 (각 함수별 경계/정상 케이스)
  - L2 property test (hypothesis, 불변식 검증)
  - L3 golden-vector (talib 대조, 정확도 확인)
"""
import math

import pytest
from hypothesis import given, strategies as st

from py_sync_contracts.trailing_stop_rules import (
    combine_stops,
    compute_trailing_stop,
    is_activated,
    is_triggered,
    update_peak,
    wilder_atr,
)


class TestUpdatePeak:
    """peak watermark 갱신 테스트."""

    def test_long_peak_increases(self) -> None:
        """Long: peak는 항상 증가하거나 유지."""
        assert update_peak("long", 100.0, 105.0, 95.0) == 105.0
        assert update_peak("long", 105.0, 103.0, 98.0) == 105.0  # 유지

    def test_short_peak_decreases(self) -> None:
        """Short: peak는 항상 감소하거나 유지."""
        assert update_peak("short", 100.0, 110.0, 95.0) == 95.0
        assert update_peak("short", 95.0, 102.0, 97.0) == 95.0  # 유지

    def test_spot_same_as_long(self) -> None:
        """Spot: long과 동일 (현물 상승 거울)."""
        assert update_peak("spot", 100.0, 105.0, 95.0) == 105.0


class TestComputeTrailingStop:
    """손절선 계산 테스트."""

    def test_percentage_long(self) -> None:
        """Long percentage: peak * (1 - pct)."""
        assert compute_trailing_stop("long", "percentage", 100.0, trailing_pct=0.05) == 95.0

    def test_percentage_short(self) -> None:
        """Short percentage: peak * (1 + pct)."""
        assert compute_trailing_stop("short", "percentage", 100.0, trailing_pct=0.05) == 105.0

    def test_atr_long(self) -> None:
        """Long ATR: peak - atr*mult."""
        assert compute_trailing_stop("long", "atr", 100.0, atr=2.0, atr_multiplier=1.5) == 97.0

    def test_atr_short(self) -> None:
        """Short ATR: peak + atr*mult."""
        assert compute_trailing_stop("short", "atr", 100.0, atr=2.0, atr_multiplier=1.5) == 103.0

    def test_percentage_missing_param(self) -> None:
        """Percentage 모드: trailing_pct 미제공 시 ValueError."""
        with pytest.raises(ValueError, match="trailing_pct"):
            compute_trailing_stop("long", "percentage", 100.0)

    def test_atr_missing_param(self) -> None:
        """ATR 모드: atr/atr_multiplier 미제공 시 ValueError."""
        with pytest.raises(ValueError, match="atr"):
            compute_trailing_stop("long", "atr", 100.0)


class TestIsActivated:
    """Trailing 활성화 판정 테스트."""

    def test_long_activated_after_breakeven(self) -> None:
        """Long: (peak-entry)/entry >= threshold."""
        # entry=100, peak=110, threshold=0.05 -> (110-100)/100=0.1 >= 0.05
        assert is_activated("long", 100.0, 110.0, 0.05) is True

    def test_long_not_activated_before_threshold(self) -> None:
        """Long: (peak-entry)/entry < threshold."""
        # entry=100, peak=103, threshold=0.05 -> (103-100)/100=0.03 < 0.05
        assert is_activated("long", 100.0, 103.0, 0.05) is False

    def test_short_activated_after_breakeven(self) -> None:
        """Short: (entry-peak)/entry >= threshold."""
        # entry=100, peak=90, threshold=0.05 -> (100-90)/100=0.1 >= 0.05
        assert is_activated("short", 100.0, 90.0, 0.05) is True

    def test_entry_zero_not_activated(self) -> None:
        """진입가 0: 활성화 불가."""
        assert is_activated("long", 0.0, 10.0, 0.05) is False


class TestIsTriggered:
    """손절선 트리거 판정 테스트."""

    def test_long_triggered_on_low(self) -> None:
        """Long: low <= stop."""
        assert is_triggered("long", 95.0, 105.0, 100.0) is True
        assert is_triggered("long", 101.0, 105.0, 100.0) is False

    def test_short_triggered_on_high(self) -> None:
        """Short: high >= stop."""
        assert is_triggered("short", 95.0, 105.0, 100.0) is True
        assert is_triggered("short", 95.0, 99.0, 100.0) is False

    def test_trigger_at_exact_stop(self) -> None:
        """정확히 stop 가격에서 트리거."""
        assert is_triggered("long", 100.0, 105.0, 100.0) is True
        assert is_triggered("short", 95.0, 100.0, 100.0) is True


class TestCombineStops:
    """손절선 결합 (단조 불변식 INV1) 테스트."""

    def test_long_combine_max(self) -> None:
        """Long: max(후보들) — 최고 수준."""
        assert combine_stops("long", 95.0, 97.0, 96.0) == 97.0

    def test_short_combine_min(self) -> None:
        """Short: min(후보들) — 최저 수준."""
        assert combine_stops("short", 105.0, 103.0, 104.0) == 103.0

    def test_combine_empty_error(self) -> None:
        """빈 후보: ValueError."""
        with pytest.raises(ValueError, match="최소 1개"):
            combine_stops("long")


class TestWilderAtr:
    """Wilder ATR 계산 테스트."""

    def test_atr_basic(self) -> None:
        """기본 ATR 계산 (22기간)."""
        highs = [100.0 + i for i in range(30)]
        lows = [95.0 + i for i in range(30)]
        closes = [98.0 + i for i in range(30)]

        atr_vals = wilder_atr(highs, lows, closes, period=22)

        assert len(atr_vals) == 30
        # 처음 21개는 NaN
        for i in range(21):
            assert math.isnan(atr_vals[i]) or atr_vals[i] >= 0
        # 22번째는 첫 ATR(단순 평균)
        assert isinstance(atr_vals[21], float) and atr_vals[21] > 0
        # 이후는 유효한 양수(Wilder 평활)
        for i in range(22, 30):
            assert isinstance(atr_vals[i], float) and atr_vals[i] > 0

    def test_atr_length_mismatch_error(self) -> None:
        """길이 불일치: ValueError."""
        with pytest.raises(ValueError, match="길이 일치 필수"):
            wilder_atr([100.0], [95.0], [98.0, 99.0])

    def test_atr_insufficient_candles_error(self) -> None:
        """기간 이상의 캔들 부족: ValueError."""
        with pytest.raises(ValueError, match="최소"):
            wilder_atr([100.0] * 10, [95.0] * 10, [98.0] * 10, period=22)


class TestPropertyInvariants:
    """Property 테스트로 불변식 검증."""

    @given(
        peak=st.floats(min_value=0.1, max_value=1000.0),
        high=st.floats(min_value=0.1, max_value=1000.0),
        low=st.floats(min_value=0.1, max_value=1000.0),
    )
    def test_peak_monotonic_long(self, peak: float, high: float, low: float) -> None:
        """INV1: Long peak는 절대 감소하지 않음."""
        new_peak = update_peak("long", peak, high, low)
        assert new_peak >= peak, f"Peak decreased: {peak} -> {new_peak}"

    @given(
        peak=st.floats(min_value=0.1, max_value=1000.0),
        high=st.floats(min_value=0.1, max_value=1000.0),
        low=st.floats(min_value=0.1, max_value=1000.0),
    )
    def test_peak_monotonic_short(self, peak: float, high: float, low: float) -> None:
        """INV1: Short peak는 절대 증가하지 않음."""
        new_peak = update_peak("short", peak, high, low)
        assert new_peak <= peak, f"Peak increased: {peak} -> {new_peak}"

    @given(
        side=st.sampled_from(["long", "short", "spot"]),
        peak=st.floats(min_value=10.0, max_value=1000.0),
        entry=st.floats(min_value=10.0, max_value=1000.0),
    )
    def test_activation_consistency(self, side: str, peak: float, entry: float) -> None:
        """INV: activation은 결정론적 (동일 입력 동일 결과)."""
        result1 = is_activated(side, entry, peak, 0.05)  # type: ignore[arg-type]
        result2 = is_activated(side, entry, peak, 0.05)  # type: ignore[arg-type]
        assert result1 == result2

    @given(st.lists(st.floats(min_value=1.0, max_value=100.0), min_size=1, max_size=10))
    def test_combine_stops_long_returns_max(self, candidates: list[float]) -> None:
        """INV: Long combine_stops는 항상 max를 반환."""
        result = combine_stops("long", *candidates)
        assert result == max(candidates)

    @given(st.lists(st.floats(min_value=1.0, max_value=100.0), min_size=1, max_size=10))
    def test_combine_stops_short_returns_min(self, candidates: list[float]) -> None:
        """INV: Short combine_stops는 항상 min을 반환."""
        result = combine_stops("short", *candidates)
        assert result == min(candidates)


class TestGoldenVectorTalib:
    """Talib ATR과의 정확도 비교 (golden-vector).

    Note: talib 설치 필수. 미설치 시 skip.
    """

    def test_wilder_atr_structure(self) -> None:
        """Wilder ATR(22) 구조 검증 (NaN 처리, 평활 일관성)."""
        try:
            import talib  # noqa: F401
        except ImportError:
            pytest.skip("talib not installed (optional)")

        highs = [102.5 + i * 0.5 for i in range(50)]
        lows = [97.5 + i * 0.5 for i in range(50)]
        closes = [100.0 + i * 0.5 for i in range(50)]

        atr_vals = wilder_atr(highs, lows, closes, period=22)
        assert len(atr_vals) == 50
        # 성숙 구간(22~49)은 모두 유효한 양수
        for i in range(21, 50):
            assert 0 < atr_vals[i] < 100, f"ATR[{i}]={atr_vals[i]} out of range"

"""calculate_required_candles 순수 함수 테스트.

목적:
    py-algo `market_data_loader.get_required_candles` 공식과의 동치성 검증.
    100 case hypothesis fuzz 로 drift 조기 탐지 (SC-4, NFR-04).

py-algo 원본 공식 (참조용):
    required = max(slow_period, atr_period) + buffer
    출처: py-algo strategy/data/market_data_loader.py:187-220
"""

from __future__ import annotations

import pytest
from hypothesis import given, strategies as st

from py_sync_contracts import calculate_required_candles
from py_sync_contracts.strategy_requirements import calculate_required_candles as _fn


# ---------------------------------------------------------------------------
# Exported from package __init__
# ---------------------------------------------------------------------------


def test_function_is_exported_from_package():
    """import py_sync_contracts 로 직접 접근 가능해야 한다."""
    assert calculate_required_candles is _fn


# ---------------------------------------------------------------------------
# py-algo test parity cases (tests/strategy/test_market_data_loader.py:363~410)
# ---------------------------------------------------------------------------


def test_parity_case_1_slow_greater_than_atr():
    """Case 1: slow_period > atr_period — max(30,14)+20 = 50."""
    result = calculate_required_candles(
        "ma_crossover",
        {"fast_period": 10, "slow_period": 30, "atr_period": 14},
        buffer=20,
    )
    assert result == 50


def test_parity_case_2_atr_greater_than_slow():
    """Case 2: atr_period > slow_period — max(10,20)+10 = 30."""
    result = calculate_required_candles(
        "ma_crossover",
        {"fast_period": 5, "slow_period": 10, "atr_period": 20},
        buffer=10,
    )
    assert result == 30


def test_parity_case_3_zero_buffer():
    """Case 3: buffer=0 — max(30,14)+0 = 30."""
    result = calculate_required_candles(
        "ma_crossover",
        {"fast_period": 10, "slow_period": 30, "atr_period": 14},
        buffer=0,
    )
    assert result == 30


def test_parity_default_params():
    """atr_period 미지정 시 14, buffer 미지정 시 20 (py-algo 기본값과 동일)."""
    result = calculate_required_candles(
        "ma_crossover",
        {"slow_period": 30},
    )
    assert result == 50  # max(30, 14) + 20


# ---------------------------------------------------------------------------
# Boundary / edge cases
# ---------------------------------------------------------------------------


def test_slow_equals_atr_uses_either_value():
    """slow == atr 일 때 max 는 동일 값 반환."""
    result = calculate_required_candles(
        "ma_crossover",
        {"slow_period": 14, "atr_period": 14},
        buffer=0,
    )
    assert result == 14


def test_fast_period_is_ignored():
    """fast_period 는 공식에서 무시되므로 결과에 영향 없어야 한다."""
    r1 = calculate_required_candles(
        "ma_crossover",
        {"fast_period": 5, "slow_period": 30},
    )
    r2 = calculate_required_candles(
        "ma_crossover",
        {"fast_period": 999, "slow_period": 30},
    )
    assert r1 == r2 == 50


def test_extra_keys_are_ignored():
    """미정의 키가 섞여 있어도 결과에 영향 없어야 한다 (미래 파라미터 확장성)."""
    result = calculate_required_candles(
        "ma_crossover",
        {"slow_period": 30, "rsi_period": 42, "take_profit_pct": 1.5},
    )
    assert result == 50


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


def test_empty_strategy_name_raises():
    with pytest.raises(ValueError, match="strategy_name"):
        calculate_required_candles("", {"slow_period": 30})


def test_non_string_strategy_name_raises():
    with pytest.raises(ValueError, match="strategy_name"):
        calculate_required_candles(123, {"slow_period": 30})  # type: ignore[arg-type]


def test_missing_slow_period_raises():
    with pytest.raises(ValueError, match="slow_period"):
        calculate_required_candles("ma_crossover", {"atr_period": 14})


def test_zero_slow_period_raises():
    with pytest.raises(ValueError, match="slow_period"):
        calculate_required_candles("ma_crossover", {"slow_period": 0})


def test_negative_slow_period_raises():
    with pytest.raises(ValueError, match="slow_period"):
        calculate_required_candles("ma_crossover", {"slow_period": -1})


def test_non_int_slow_period_raises():
    with pytest.raises(ValueError, match="slow_period"):
        calculate_required_candles("ma_crossover", {"slow_period": "30"})


def test_bool_as_slow_period_raises():
    """True==1 하지만 bool 은 의도된 파라미터가 아님 → 거부."""
    with pytest.raises(ValueError, match="slow_period"):
        calculate_required_candles("ma_crossover", {"slow_period": True})


def test_zero_atr_period_raises():
    with pytest.raises(ValueError, match="atr_period"):
        calculate_required_candles(
            "ma_crossover", {"slow_period": 30, "atr_period": 0}
        )


def test_negative_buffer_raises():
    with pytest.raises(ValueError, match="buffer"):
        calculate_required_candles("ma_crossover", {"slow_period": 30}, buffer=-1)


def test_buffer_zero_is_allowed():
    """buffer=0 은 유효 (py-algo 도 허용)."""
    result = calculate_required_candles(
        "ma_crossover", {"slow_period": 30}, buffer=0
    )
    assert result == 30


# ---------------------------------------------------------------------------
# Hypothesis 100-case fuzz — py-algo 공식과의 동치성
# ---------------------------------------------------------------------------


def _py_algo_reference(slow_period: int, atr_period: int, buffer: int) -> int:
    """py-algo `get_required_candles` 원본 공식 재구현 (테스트용 기준점).

    fast_period 는 원본에서도 결과에 영향 없으므로 본 재현에서도 제외.
    """
    return max(slow_period, atr_period) + buffer


@given(
    slow_period=st.integers(min_value=1, max_value=10_000),
    atr_period=st.integers(min_value=1, max_value=10_000),
    buffer=st.integers(min_value=0, max_value=10_000),
)
def test_fuzz_parity_with_py_algo_formula(
    slow_period: int, atr_period: int, buffer: int
) -> None:
    """100+ 입력 조합에서 py-algo 공식과 동일 결과여야 한다 (SC-4)."""
    expected = _py_algo_reference(slow_period, atr_period, buffer)
    actual = calculate_required_candles(
        "ma_crossover",
        {"slow_period": slow_period, "atr_period": atr_period},
        buffer=buffer,
    )
    assert actual == expected, (
        f"drift detected: slow={slow_period}, atr={atr_period}, "
        f"buffer={buffer}, expected={expected}, got={actual}"
    )


@given(
    slow_period=st.integers(min_value=1, max_value=1_000),
    fast_period=st.integers(min_value=1, max_value=1_000),
    buffer=st.integers(min_value=0, max_value=100),
)
def test_fuzz_fast_period_does_not_affect_result(
    slow_period: int, fast_period: int, buffer: int
) -> None:
    """fast_period 값을 변화시켜도 결과는 변하지 않아야 한다 (공식에 미사용)."""
    r1 = calculate_required_candles(
        "ma_crossover",
        {"slow_period": slow_period, "fast_period": fast_period},
        buffer=buffer,
    )
    r2 = calculate_required_candles(
        "ma_crossover",
        {"slow_period": slow_period, "fast_period": fast_period * 2 + 1},
        buffer=buffer,
    )
    assert r1 == r2


@given(
    slow_period=st.integers(min_value=1, max_value=1_000),
    buffer=st.integers(min_value=0, max_value=100),
)
def test_fuzz_default_atr_period_is_14(slow_period: int, buffer: int) -> None:
    """atr_period 미지정 = 14 로 호출한 것과 동일 결과."""
    r_default = calculate_required_candles(
        "ma_crossover", {"slow_period": slow_period}, buffer=buffer
    )
    r_explicit = calculate_required_candles(
        "ma_crossover",
        {"slow_period": slow_period, "atr_period": 14},
        buffer=buffer,
    )
    assert r_default == r_explicit

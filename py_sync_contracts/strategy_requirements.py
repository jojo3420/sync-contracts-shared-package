"""전략별 요구 캔들 개수 산출 공식 (SSoT).

Publisher(trading-admin-dashboard)와 Subscriber(py-algo-stragegy-system-v1)가
동일한 공식을 공유하기 위한 순수 함수 모듈. 어느 쪽도 자체 하드코딩을 금지하고
반드시 이 모듈을 import 해야 drift 가 발생하지 않는다.

공식 출처:
    py-algo `strategy/data/market_data_loader.py:187-220` 의 `get_required_candles`
    를 v0.4.0 에서 sync-contracts 로 승격. 이후 py-algo 는 본 모듈을 import 하여
    재사용한다 (environment.yml @v0.4.0 참조).

버전 규칙:
    - minor bump: 새 strategy 분기 추가 (하위 호환)
    - major bump: 기존 분기의 공식 변경 (파괴적 변경)
"""

from __future__ import annotations

from typing import Any, Mapping


__all__ = ["calculate_required_candles"]


def calculate_required_candles(
    strategy_name: str,
    parameters: Mapping[str, Any],
    buffer: int = 20,
) -> int:
    """전략 실행에 필요한 최소 캔들 개수를 산출한다.

    MA 계열 전략 공식:
        required = max(slow_period, atr_period) + buffer

    fast_period 는 공식에 사용하지 않지만 API 일관성을 위해 parameters 에
    포함되어 있어도 무시한다. py-algo `get_required_candles` 시그니처와 동치이며,
    같은 입력에 대해 반드시 같은 결과를 반환해야 한다 (SC-4).

    Args:
        strategy_name: 전략 이름. 로그 및 향후 전략별 분기 확장용. 빈 문자열 금지.
        parameters: 전략 parameters dict.
            필수 키: "slow_period" (int ≥ 1).
            선택 키: "atr_period" (int ≥ 1, 기본 14).
            기타 키는 무시된다.
        buffer: 추가 여유분. 0 이상 정수 (기본 20).

    Returns:
        int: 필요한 최소 캔들 개수.

    Raises:
        ValueError: strategy_name 이 빈 문자열, parameters 에 slow_period 누락,
                    slow_period/atr_period/buffer 가 음수 또는 0(slow/atr), 정수 아님.

    Examples:
        >>> calculate_required_candles("ma_crossover", {"slow_period": 30})
        50
        >>> calculate_required_candles(
        ...     "ma_crossover",
        ...     {"fast_period": 10, "slow_period": 30, "atr_period": 14},
        ...     buffer=20,
        ... )
        50
        >>> calculate_required_candles(
        ...     "ma_crossover",
        ...     {"slow_period": 10, "atr_period": 20},
        ...     buffer=10,
        ... )
        30
    """
    if not strategy_name or not isinstance(strategy_name, str):
        raise ValueError("strategy_name 은 비어있지 않은 문자열이어야 합니다.")

    if "slow_period" not in parameters:
        raise ValueError(
            f"parameters 에 'slow_period' 키가 필요합니다. "
            f"strategy={strategy_name}, keys={list(parameters.keys())}"
        )

    slow_period_raw = parameters["slow_period"]
    atr_period_raw = parameters.get("atr_period", 14)

    _validate_positive_int("slow_period", slow_period_raw)
    _validate_positive_int("atr_period", atr_period_raw)
    _validate_nonnegative_int("buffer", buffer)

    # validator 통과 → 정수 확정. mypy strict narrow.
    slow_period: int = slow_period_raw
    atr_period: int = atr_period_raw

    return max(slow_period, atr_period) + buffer


def _validate_positive_int(name: str, value: Any) -> None:
    # bool 은 int 의 서브클래스지만 파라미터로 오면 의미 없음 → 거부
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} 는 정수여야 합니다 (got {type(value).__name__}={value!r}).")
    if value <= 0:
        raise ValueError(f"{name} 는 1 이상이어야 합니다 (got {value}).")


def _validate_nonnegative_int(name: str, value: Any) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} 는 정수여야 합니다 (got {type(value).__name__}={value!r}).")
    if value < 0:
        raise ValueError(f"{name} 는 0 이상이어야 합니다 (got {value}).")

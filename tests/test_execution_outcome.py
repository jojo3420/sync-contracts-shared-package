"""test_execution_outcome.py — ExecutionOutcome / ExecutionReasonCode enum 완전성 테스트.

v0.7.0 에 추가된 enum 의 값·길이·whitelist 매핑을 검증한다.
strategy-execution-observability feature 의 SSoT 무결성 보호.
"""
from __future__ import annotations

import json

from py_sync_contracts import (
    OUTCOME_REASON_WHITELIST,
    ExecutionOutcome,
    ExecutionReasonCode,
    is_valid_outcome_reason,
)


class TestExecutionOutcome:
    """ExecutionOutcome enum 완전성.

    v0.7.0 초기 12 계열 — 추가 시 minor bump + 이 테스트 수 갱신.
    v0.8.0: SKIP_AUTOMATION_OFF 추가 → 13.
    v0.11.0: SKIP_NO_POSITION_TO_CLOSE + SKIP_DUPLICATE_OPEN + ERROR_DISPATCH_GUARD → 16.
    """

    def test_count_is_16(self) -> None:
        # v0.7.0: SUCCESS(1) + NO_SIGNAL(1) + SKIP(5) + ERROR(5) = 12
        # v0.8.0:  + SKIP_AUTOMATION_OFF                            = 13
        # v0.11.0: + SKIP_NO_POSITION_TO_CLOSE + SKIP_DUPLICATE_OPEN
        #          + ERROR_DISPATCH_GUARD (signal-guard-defense-in-depth) = 16
        assert len(ExecutionOutcome) == 16

    def test_all_values_are_strings(self) -> None:
        for member in ExecutionOutcome:
            assert isinstance(member.value, str)

    def test_all_values_within_db_varchar32(self) -> None:
        """DB 컬럼 outcome VARCHAR(32) 와 정합 — 추가 시 길이 초과 원천 차단."""
        for member in ExecutionOutcome:
            assert len(member.value) <= 32, (
                f"ExecutionOutcome.{member.name}='{member.value}' "
                f"길이 {len(member.value)} > 32. "
                f"strategy_execution_log.outcome VARCHAR(32) 초과."
            )

    def test_str_subtype_serializes_directly(self) -> None:
        # str Enum 이므로 json.dumps 없이 value 로 직렬화 가능.
        assert json.dumps(ExecutionOutcome.SUCCESS_SIGNAL.value) == '"SUCCESS_SIGNAL"'

    def test_known_values(self) -> None:
        # v0.7.0 초기 셋
        assert ExecutionOutcome.SUCCESS_SIGNAL.value == "SUCCESS_SIGNAL"
        assert ExecutionOutcome.NO_SIGNAL_HOLD.value == "NO_SIGNAL_HOLD"
        assert ExecutionOutcome.SKIP_REGIME_MISMATCH.value == "SKIP_REGIME_MISMATCH"
        assert ExecutionOutcome.SKIP_FILTER_REJECTED.value == "SKIP_FILTER_REJECTED"
        assert ExecutionOutcome.SKIP_STALE_DATA.value == "SKIP_STALE_DATA"
        assert ExecutionOutcome.SKIP_ORDER_VALUE_UNDER_MIN.value == "SKIP_ORDER_VALUE_UNDER_MIN"
        assert ExecutionOutcome.SKIP_SYMBOL_DEPRECATED.value == "SKIP_SYMBOL_DEPRECATED"
        assert ExecutionOutcome.ERROR_STRATEGY_EXCEPTION.value == "ERROR_STRATEGY_EXCEPTION"
        assert ExecutionOutcome.ERROR_EXCHANGE_API.value == "ERROR_EXCHANGE_API"
        assert ExecutionOutcome.ERROR_ORDER_API.value == "ERROR_ORDER_API"
        assert ExecutionOutcome.ERROR_NETWORK.value == "ERROR_NETWORK"
        assert ExecutionOutcome.ERROR_UNKNOWN.value == "ERROR_UNKNOWN"

    def test_roundtrip_from_string(self) -> None:
        assert ExecutionOutcome("SUCCESS_SIGNAL") is ExecutionOutcome.SUCCESS_SIGNAL
        assert ExecutionOutcome("NO_SIGNAL_HOLD") is ExecutionOutcome.NO_SIGNAL_HOLD
        assert ExecutionOutcome("ERROR_UNKNOWN") is ExecutionOutcome.ERROR_UNKNOWN

    def test_categorization_by_prefix(self) -> None:
        """계열별 접두사 규약 준수 검증."""
        success = [m for m in ExecutionOutcome if m.value.startswith("SUCCESS_")]
        no_signal = [m for m in ExecutionOutcome if m.value.startswith("NO_SIGNAL_")]
        skip = [m for m in ExecutionOutcome if m.value.startswith("SKIP_")]
        error = [m for m in ExecutionOutcome if m.value.startswith("ERROR_")]
        # 모두 접두사 중 하나에 속해야 한다.
        assert len(success) + len(no_signal) + len(skip) + len(error) == len(ExecutionOutcome)
        assert len(success) >= 1
        assert len(no_signal) >= 1
        assert len(skip) >= 1
        assert len(error) >= 1


class TestExecutionReasonCode:
    """ExecutionReasonCode enum 완전성.

    v0.7.0 초기 약 30종 — 값 추가 시 minor bump.
    v0.8.0: SKIP_ORDER_AUTOMATION_OFF 추가 → 32.
    v0.10.0: SIGNAL_VALIDATION_FAILED 추가 → 33.
    v0.11.0: CLOSE_WITHOUT_POSITION + DUPLICATE_OPEN_DENIED + DISPATCH_GUARD_FAILED → 36.
    """

    def test_count_matches_v0110(self) -> None:
        # v0.7.0 기준 31종. 추가 시 테스트 갱신 필수.
        # 내역: SUCCESS(2) + HOLD(2) + REGIME(2) + FILTER(3) + STALE(2)
        #     + ORDER_VAL(3) + DEPRECATED(2) + STRATEGY_EXC(2) + CCXT(4)
        #     + ORDER_API(4) + NETWORK(3) + UNKNOWN(2) = 31.
        # v0.8.0:  + SKIP_ORDER_AUTOMATION_OFF                          = 32.
        # v0.10.0: + SIGNAL_VALIDATION_FAILED                           = 33.
        # v0.11.0: + CLOSE_WITHOUT_POSITION + DUPLICATE_OPEN_DENIED
        #          + DISPATCH_GUARD_FAILED (signal-guard-defense-in-depth) = 36.
        assert len(ExecutionReasonCode) == 36

    def test_all_values_within_db_varchar64(self) -> None:
        """DB 컬럼 reason_code VARCHAR(64) 정합."""
        for member in ExecutionReasonCode:
            assert len(member.value) <= 64, (
                f"ExecutionReasonCode.{member.name}='{member.value}' "
                f"길이 {len(member.value)} > 64."
            )

    def test_str_subtype_serializes_directly(self) -> None:
        assert (
            json.dumps(ExecutionReasonCode.HOLD_NO_CROSSOVER.value)
            == '"HOLD_NO_CROSSOVER"'
        )

    def test_signal_buy_sell_present(self) -> None:
        assert ExecutionReasonCode.SIGNAL_BUY.value == "SIGNAL_BUY"
        assert ExecutionReasonCode.SIGNAL_SELL.value == "SIGNAL_SELL"

    def test_cycle_incomplete_present(self) -> None:
        # 사이클 완결성 검증용 reason (Plan §Idea 1).
        assert (
            ExecutionReasonCode.CYCLE_INCOMPLETE_UNMAPPED.value
            == "CYCLE_INCOMPLETE_UNMAPPED"
        )

    def test_unclassified_fallback_present(self) -> None:
        # ERROR_UNKNOWN 의 기본 reason. 미분류 예외 fallback.
        assert ExecutionReasonCode.UNCLASSIFIED.value == "UNCLASSIFIED"


class TestOutcomeReasonWhitelist:
    """outcome ↔ reason_code 조합 whitelist 매핑 검증 (misuse-proof)."""

    def test_all_outcomes_present_in_whitelist(self) -> None:
        # 모든 ExecutionOutcome 이 whitelist 에 포함되어야 한다.
        assert set(OUTCOME_REASON_WHITELIST.keys()) == set(ExecutionOutcome)

    def test_success_signal_requires_buy_or_sell(self) -> None:
        # SUCCESS_SIGNAL 은 반드시 BUY 또는 SELL — None 불허.
        allowed = OUTCOME_REASON_WHITELIST[ExecutionOutcome.SUCCESS_SIGNAL]
        assert ExecutionReasonCode.SIGNAL_BUY in allowed
        assert ExecutionReasonCode.SIGNAL_SELL in allowed
        assert None not in allowed

    def test_hold_allows_none(self) -> None:
        # NO_SIGNAL_HOLD 는 세부 분류 불가 케이스 대비 None 허용.
        allowed = OUTCOME_REASON_WHITELIST[ExecutionOutcome.NO_SIGNAL_HOLD]
        assert None in allowed

    def test_error_unknown_only_allows_unclassified_or_cycle_incomplete(self) -> None:
        allowed = OUTCOME_REASON_WHITELIST[ExecutionOutcome.ERROR_UNKNOWN]
        assert ExecutionReasonCode.UNCLASSIFIED in allowed
        assert ExecutionReasonCode.CYCLE_INCOMPLETE_UNMAPPED in allowed
        # 다른 계열 reason 은 불허
        assert ExecutionReasonCode.SIGNAL_BUY not in allowed
        assert ExecutionReasonCode.CCXT_TIMEOUT not in allowed

    def test_is_valid_outcome_reason_accepts_whitelisted(self) -> None:
        assert is_valid_outcome_reason(
            ExecutionOutcome.SUCCESS_SIGNAL,
            ExecutionReasonCode.SIGNAL_BUY,
        )
        assert is_valid_outcome_reason(
            ExecutionOutcome.NO_SIGNAL_HOLD,
            ExecutionReasonCode.HOLD_NO_CROSSOVER,
        )
        assert is_valid_outcome_reason(
            ExecutionOutcome.NO_SIGNAL_HOLD,
            None,  # HOLD 는 None 허용
        )

    def test_is_valid_outcome_reason_rejects_mismatched(self) -> None:
        # SUCCESS_SIGNAL 에 HOLD reason 할당 불허
        assert not is_valid_outcome_reason(
            ExecutionOutcome.SUCCESS_SIGNAL,
            ExecutionReasonCode.HOLD_NO_CROSSOVER,
        )
        # SUCCESS_SIGNAL 에 None 불허
        assert not is_valid_outcome_reason(
            ExecutionOutcome.SUCCESS_SIGNAL,
            None,
        )
        # ERROR_EXCHANGE_API 에 ORDER_API reason 불허
        assert not is_valid_outcome_reason(
            ExecutionOutcome.ERROR_EXCHANGE_API,
            ExecutionReasonCode.ORDER_API_5XX,
        )

    def test_all_reason_codes_appear_in_some_whitelist(self) -> None:
        """정의된 모든 reason_code 가 최소 1개 outcome 에 매핑되어야 한다.

        사용처 없는 reason_code 는 dead code → 존재 금지.
        """
        all_used: set[ExecutionReasonCode] = set()
        for allowed in OUTCOME_REASON_WHITELIST.values():
            for r in allowed:
                if r is not None:
                    all_used.add(r)
        unused = set(ExecutionReasonCode) - all_used
        assert unused == set(), (
            f"whitelist 에 매핑되지 않은 reason_code: {unused}"
        )

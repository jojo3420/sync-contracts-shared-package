"""전략 사이클 실행 결과 outcome / reason_code enum 모듈.

py-algo `StrategyDispatcherJob → StrategyIterator → SignalOrchestrator` 가
매 사이클 × (전략, 거래소, 심볼) 조합마다 생성하는 실행 결과를 분류하는 SSoT.
dashboard `strategy_execution_log` 테이블의 `outcome` / `reason_code` 컬럼과
1:1 대응.

Design Ref: trading-admin-dashboard docs/02-design/features/
            strategy-execution-observability.design.md §3.4
Plan SC: SC-2 — py-algo 모든 계측 지점에서 outcome+reason_code 생성.

버전 이력:
    v0.7.0: 초기 도입 (strategy-execution-observability feature).
            ExecutionOutcome 12종 + ExecutionReasonCode 약 30종.
            py-algo Writer + dashboard canonical 양쪽 공유 계약.

버전 규칙:
    - minor bump: 새 outcome/reason 값 추가 (하위 호환).
    - major bump: outcome/reason 값 삭제·이름 변경 (파괴적 변경).
"""
from __future__ import annotations

from enum import Enum


class ExecutionOutcome(str, Enum):
    """전략 사이클 결정 분기 최종 판정.

    str Enum 이므로 json.dumps 없이 .value 로 직렬화 가능.
    DB 컬럼 `strategy_execution_log.outcome VARCHAR(32)` 와 길이 정합.

    계열별 접두사 규약:
        - SUCCESS_*: 실제 시그널 전송 성공 (happy path).
        - NO_SIGNAL_*: 전략 정상 실행, 조건 미충족으로 시그널 미발생 (happy path).
        - SKIP_*: 전략 정상, 특정 사유로 건너뜀 (필터·국면·최소금액·상장폐지 등).
        - ERROR_*: 예외 발생 (전략/거래소/주문 API/네트워크/미분류).
    """

    # ── SUCCESS ─────────────────────────────────────────────────────────
    SUCCESS_SIGNAL = "SUCCESS_SIGNAL"
    # ── NO SIGNAL (happy hold) ─────────────────────────────────────────
    NO_SIGNAL_HOLD = "NO_SIGNAL_HOLD"
    # ── SKIP (정상 건너뜀) ──────────────────────────────────────────────
    SKIP_REGIME_MISMATCH = "SKIP_REGIME_MISMATCH"
    SKIP_FILTER_REJECTED = "SKIP_FILTER_REJECTED"
    SKIP_STALE_DATA = "SKIP_STALE_DATA"
    SKIP_ORDER_VALUE_UNDER_MIN = "SKIP_ORDER_VALUE_UNDER_MIN"
    SKIP_SYMBOL_DEPRECATED = "SKIP_SYMBOL_DEPRECATED"
    # ── ERROR (예외) ───────────────────────────────────────────────────
    ERROR_STRATEGY_EXCEPTION = "ERROR_STRATEGY_EXCEPTION"
    ERROR_EXCHANGE_API = "ERROR_EXCHANGE_API"
    ERROR_ORDER_API = "ERROR_ORDER_API"
    ERROR_NETWORK = "ERROR_NETWORK"
    ERROR_UNKNOWN = "ERROR_UNKNOWN"


class ExecutionReasonCode(str, Enum):
    """ExecutionOutcome 의 세부 원인 코드.

    DB 컬럼 `strategy_execution_log.reason_code VARCHAR(64)` 와 길이 정합.
    outcome 과 쌍으로만 의미를 가지며, outcome 계열별로 묶어서 정의한다.
    nullable — SUCCESS_SIGNAL 외 outcome 에서 분류 불가 시 None 허용.
    """

    # ── SUCCESS_SIGNAL ─────────────────────────────────────────────────
    SIGNAL_BUY = "SIGNAL_BUY"
    SIGNAL_SELL = "SIGNAL_SELL"
    # ── NO_SIGNAL_HOLD ─────────────────────────────────────────────────
    HOLD_NO_CROSSOVER = "HOLD_NO_CROSSOVER"
    HOLD_CONDITION_NOT_MET = "HOLD_CONDITION_NOT_MET"
    # ── SKIP_REGIME_MISMATCH ───────────────────────────────────────────
    REGIME_BEAR_EXPECTED_BULL = "REGIME_BEAR_EXPECTED_BULL"
    REGIME_SIDEWAYS_FILTERED = "REGIME_SIDEWAYS_FILTERED"
    # ── SKIP_FILTER_REJECTED ───────────────────────────────────────────
    CONFIRMATION_BARS_NOT_MET = "CONFIRMATION_BARS_NOT_MET"
    MIN_SPREAD_BELOW = "MIN_SPREAD_BELOW"
    VOLUME_TOO_LOW = "VOLUME_TOO_LOW"
    # ── SKIP_STALE_DATA ────────────────────────────────────────────────
    OHLCV_STALE = "OHLCV_STALE"
    LAST_CANDLE_OLD = "LAST_CANDLE_OLD"
    # ── SKIP_ORDER_VALUE_UNDER_MIN ─────────────────────────────────────
    UNDER_10K_KRW_UPBIT = "UNDER_10K_KRW_UPBIT"
    UNDER_MIN_USDT_BITGET = "UNDER_MIN_USDT_BITGET"
    ORDER_VALUE_UNSUPPORTED_EXCHANGE = "ORDER_VALUE_UNSUPPORTED_EXCHANGE"
    # ── SKIP_SYMBOL_DEPRECATED ─────────────────────────────────────────
    LISTING_DEPRECATED_UPBIT = "LISTING_DEPRECATED_UPBIT"
    LISTING_DEPRECATED_BITGET = "LISTING_DEPRECATED_BITGET"
    # ── ERROR_STRATEGY_EXCEPTION ───────────────────────────────────────
    GENERATE_SIGNALS_FAILED = "GENERATE_SIGNALS_FAILED"
    REGIME_CLASSIFIER_FAILED = "REGIME_CLASSIFIER_FAILED"
    # ── ERROR_EXCHANGE_API ─────────────────────────────────────────────
    CCXT_TIMEOUT = "CCXT_TIMEOUT"
    CCXT_5XX = "CCXT_5XX"
    CCXT_AUTH_FAILED = "CCXT_AUTH_FAILED"
    CCXT_RATELIMIT = "CCXT_RATELIMIT"
    # ── ERROR_ORDER_API ────────────────────────────────────────────────
    ORDER_API_4XX = "ORDER_API_4XX"
    ORDER_API_5XX = "ORDER_API_5XX"
    ORDER_API_TIMEOUT = "ORDER_API_TIMEOUT"
    ORDER_API_IDEMPOTENCY_CONFLICT = "ORDER_API_IDEMPOTENCY_CONFLICT"
    # ── ERROR_NETWORK ──────────────────────────────────────────────────
    CONNECTION_REFUSED = "CONNECTION_REFUSED"
    DNS_FAILED = "DNS_FAILED"
    TLS_HANDSHAKE_FAILED = "TLS_HANDSHAKE_FAILED"
    # ── ERROR_UNKNOWN ──────────────────────────────────────────────────
    UNCLASSIFIED = "UNCLASSIFIED"
    CYCLE_INCOMPLETE_UNMAPPED = "CYCLE_INCOMPLETE_UNMAPPED"


# outcome → 허용 reason_code 매핑 (정적 검증 테이블).
# Collector 가 record() 시 이 매핑으로 misuse-proof 검증 가능.
# Design Ref: senior-mindset §4 Misuse-proof — 잘못된 조합 원천 차단.
OUTCOME_REASON_WHITELIST: dict[ExecutionOutcome, frozenset[ExecutionReasonCode | None]] = {
    ExecutionOutcome.SUCCESS_SIGNAL: frozenset({
        ExecutionReasonCode.SIGNAL_BUY,
        ExecutionReasonCode.SIGNAL_SELL,
    }),
    ExecutionOutcome.NO_SIGNAL_HOLD: frozenset({
        ExecutionReasonCode.HOLD_NO_CROSSOVER,
        ExecutionReasonCode.HOLD_CONDITION_NOT_MET,
        None,  # 세부 분류 불가 시 허용
    }),
    ExecutionOutcome.SKIP_REGIME_MISMATCH: frozenset({
        ExecutionReasonCode.REGIME_BEAR_EXPECTED_BULL,
        ExecutionReasonCode.REGIME_SIDEWAYS_FILTERED,
        None,
    }),
    ExecutionOutcome.SKIP_FILTER_REJECTED: frozenset({
        ExecutionReasonCode.CONFIRMATION_BARS_NOT_MET,
        ExecutionReasonCode.MIN_SPREAD_BELOW,
        ExecutionReasonCode.VOLUME_TOO_LOW,
        None,
    }),
    ExecutionOutcome.SKIP_STALE_DATA: frozenset({
        ExecutionReasonCode.OHLCV_STALE,
        ExecutionReasonCode.LAST_CANDLE_OLD,
        None,
    }),
    ExecutionOutcome.SKIP_ORDER_VALUE_UNDER_MIN: frozenset({
        ExecutionReasonCode.UNDER_10K_KRW_UPBIT,
        ExecutionReasonCode.UNDER_MIN_USDT_BITGET,
        ExecutionReasonCode.ORDER_VALUE_UNSUPPORTED_EXCHANGE,
        None,
    }),
    ExecutionOutcome.SKIP_SYMBOL_DEPRECATED: frozenset({
        ExecutionReasonCode.LISTING_DEPRECATED_UPBIT,
        ExecutionReasonCode.LISTING_DEPRECATED_BITGET,
        None,
    }),
    ExecutionOutcome.ERROR_STRATEGY_EXCEPTION: frozenset({
        ExecutionReasonCode.GENERATE_SIGNALS_FAILED,
        ExecutionReasonCode.REGIME_CLASSIFIER_FAILED,
        None,
    }),
    ExecutionOutcome.ERROR_EXCHANGE_API: frozenset({
        ExecutionReasonCode.CCXT_TIMEOUT,
        ExecutionReasonCode.CCXT_5XX,
        ExecutionReasonCode.CCXT_AUTH_FAILED,
        ExecutionReasonCode.CCXT_RATELIMIT,
        None,
    }),
    ExecutionOutcome.ERROR_ORDER_API: frozenset({
        ExecutionReasonCode.ORDER_API_4XX,
        ExecutionReasonCode.ORDER_API_5XX,
        ExecutionReasonCode.ORDER_API_TIMEOUT,
        ExecutionReasonCode.ORDER_API_IDEMPOTENCY_CONFLICT,
        None,
    }),
    ExecutionOutcome.ERROR_NETWORK: frozenset({
        ExecutionReasonCode.CONNECTION_REFUSED,
        ExecutionReasonCode.DNS_FAILED,
        ExecutionReasonCode.TLS_HANDSHAKE_FAILED,
        None,
    }),
    ExecutionOutcome.ERROR_UNKNOWN: frozenset({
        ExecutionReasonCode.UNCLASSIFIED,
        ExecutionReasonCode.CYCLE_INCOMPLETE_UNMAPPED,
        None,
    }),
}


def is_valid_outcome_reason(
    outcome: ExecutionOutcome,
    reason: ExecutionReasonCode | None,
) -> bool:
    """outcome ↔ reason_code 조합의 whitelist 검증.

    Args:
        outcome: ExecutionOutcome 값.
        reason: ExecutionReasonCode 값 또는 None.

    Returns:
        허용된 조합이면 True. SUCCESS_SIGNAL 은 reason=None 불허.
    """
    allowed = OUTCOME_REASON_WHITELIST.get(outcome)
    if allowed is None:
        return False
    return reason in allowed

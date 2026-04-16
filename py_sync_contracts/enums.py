"""이벤트 타입 enum 모듈.

Publisher/Subscriber 양쪽이 동일 enum 값을 사용해야 wire-compatible 직렬화가 보장된다.
enum 값 추가: minor bump. enum 값 삭제/변경: major bump.
"""
from __future__ import annotations

from enum import Enum


class SyncEventType(str, Enum):
    """strategy_symbol_sync 채널 이벤트 종류 — 5종 고정 (v0.1.0).

    str Enum 이므로 json.dumps 없이 .value로 직렬화 가능.
    """

    STRATEGY_PARAMS_CHANGED = "STRATEGY_PARAMS_CHANGED"
    STRATEGY_TIMEFRAME_CHANGED = "STRATEGY_TIMEFRAME_CHANGED"
    SYMBOL_ACTIVE_CHANGED = "SYMBOL_ACTIVE_CHANGED"
    SYMBOL_STRATEGY_MAPPING_CHANGED = "SYMBOL_STRATEGY_MAPPING_CHANGED"
    SYMBOL_RISK_CHANGED = "SYMBOL_RISK_CHANGED"


class TargetType(str, Enum):
    """이벤트 대상 테이블 종류 (v0.3.0).

    값이 실제 DB 테이블명과 1:1 대응. 테이블명 변경 시 major bump.
    v0.2.0: STRATEGY_EXCHANGE_SYMBOL 추가.
    v0.3.0: schema-normalization — rename 반영 + STRATEGY_SYMBOL_MAPPING 추가.
             BACKTEST_STRATEGY, STRATEGY_TIMEFRAME_CONFIG, STRATEGY_EXCHANGE_SYMBOL deprecated.
    """

    # 현행 (renamed)
    STRATEGIES = "strategies"
    STRATEGY_TIMEFRAMES = "strategy_timeframes"
    TRADING_SYMBOLS = "trading_symbols"
    SYMBOLS = "symbols"
    SYMBOL_RISK_CONFIG = "symbol_risk_config"
    STRATEGY_SYMBOL_MAPPING = "strategy_symbol_mapping"

    # deprecated (하위호환 — Step 4에서 제거)
    BACKTEST_STRATEGY = "strategies"  # alias → same value as STRATEGIES
    STRATEGY_TIMEFRAME_CONFIG = "strategy_timeframes"  # alias
    STRATEGY_EXCHANGE_SYMBOL = "strategy_exchange_symbol"  # Step 4에서 제거


class SyncAction(str, Enum):
    """payload action 필드 허용 값.

    기존 frozenset whitelist를 타입 안전 enum으로 승격.
    SyncPayload.action 필드는 v0.1에서 str 유지, v0.2에서 SyncAction으로 강화 예정.
    """

    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"

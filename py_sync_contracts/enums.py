"""이벤트 타입 enum 모듈.

Publisher/Subscriber 양쪽이 동일 enum 값을 사용해야 wire-compatible 직렬화가 보장된다.
enum 값 추가: minor bump. enum 값 삭제/변경: major bump.
"""
from __future__ import annotations

from enum import Enum


class SyncEventType(str, Enum):
    """strategy_symbol_sync 채널 이벤트 종류.

    str Enum 이므로 json.dumps 없이 .value로 직렬화 가능.

    버전 이력:
        v0.1.0: 초기 5종 (STRATEGY_PARAMS_CHANGED, STRATEGY_TIMEFRAME_CHANGED,
                SYMBOL_ACTIVE_CHANGED, SYMBOL_STRATEGY_MAPPING_CHANGED, SYMBOL_RISK_CHANGED).
        v0.4.0: SYMBOL_COLLECTION_LINKED 추가 (symbol-mapping-auto feature — 수집 타겟
                신규 활성화 시 py-algo backfill 트리거용).
        v0.5.0: COLLECTION_TARGET_CHANGED 추가 (timeseries-rca-auto-sync feature —
                전략심볼 기반 SSoT 변경을 order-api 구독자가 APScheduler add/remove
                로 반영. action=INSERT/UPDATE/DELETE 분기).
        v0.6.0: SYMBOL_DEPRECATED 추가 (timeseries-listing-deprecated-detect feature —
                Dashboard ListingWatcherJob이 Upbit/Bitget 상장폐지 감지 시 publish.
                order-api: collection_targets.is_active=false + APScheduler remove.
                py-algo: strategy_exchange_symbol 의 paper/live_trading 비활성 + 열린
                포지션 자동 청산 금지(경고 로그만)).
    """

    STRATEGY_PARAMS_CHANGED = "STRATEGY_PARAMS_CHANGED"
    STRATEGY_TIMEFRAME_CHANGED = "STRATEGY_TIMEFRAME_CHANGED"
    SYMBOL_ACTIVE_CHANGED = "SYMBOL_ACTIVE_CHANGED"
    SYMBOL_STRATEGY_MAPPING_CHANGED = "SYMBOL_STRATEGY_MAPPING_CHANGED"
    SYMBOL_RISK_CHANGED = "SYMBOL_RISK_CHANGED"
    SYMBOL_COLLECTION_LINKED = "SYMBOL_COLLECTION_LINKED"
    # v0.5.0
    COLLECTION_TARGET_CHANGED = "COLLECTION_TARGET_CHANGED"
    # v0.6.0
    SYMBOL_DEPRECATED = "SYMBOL_DEPRECATED"


class TargetType(str, Enum):
    """이벤트 대상 테이블 종류.

    값이 실제 DB 테이블명과 1:1 대응. 테이블명 변경 시 major bump.

    버전 이력:
        v0.2.0: STRATEGY_EXCHANGE_SYMBOL 추가.
        v0.3.0: schema-normalization — rename 반영 + STRATEGY_SYMBOL_MAPPING 추가.
                 BACKTEST_STRATEGY, STRATEGY_TIMEFRAME_CONFIG, STRATEGY_EXCHANGE_SYMBOL deprecated.
        v0.4.0: COLLECTION_TARGETS 추가 (symbol-mapping-auto feature — 수집 타겟
                orchestrator 가 publish 시 target_type 으로 사용).
        v0.9.0: PAIR_TRADE_CONFIG 추가 (pair-trade-dashboard-integration feature —
                dashboard ↔ py-algo 간 페어 트레이드 enabled/paused 토글 sync.
                별도 채널 신설 대신 단일 SYNC_CHANNEL + TargetType 라우팅 모델
                재사용. Design Ref: pair-trade-dashboard-integration.design.md v0.2 §4.8).
    """

    # 현행 (renamed)
    STRATEGIES = "strategies"
    STRATEGY_TIMEFRAMES = "strategy_timeframes"
    TRADING_SYMBOLS = "trading_symbols"
    SYMBOLS = "symbols"
    SYMBOL_RISK_CONFIG = "symbol_risk_config"
    STRATEGY_SYMBOL_MAPPING = "strategy_symbol_mapping"
    COLLECTION_TARGETS = "collection_targets"
    # v0.9.0
    PAIR_TRADE_CONFIG = "pair_trade_config"

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

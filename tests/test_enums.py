"""test_enums.py — SyncEventType, TargetType, SyncAction enum 완전성 테스트."""
from __future__ import annotations

from py_sync_contracts import SyncAction, SyncEventType, TargetType


class TestSyncEventType:
    def test_count_is_7(self) -> None:
        # v0.1.0: 5종 / v0.4.0: SYMBOL_COLLECTION_LINKED 추가 → 6종.
        # v0.5.0: COLLECTION_TARGET_CHANGED 추가 → 7종.
        # 추가 시 minor bump 필요.
        assert len(SyncEventType) == 7

    def test_all_values_are_strings(self) -> None:
        for member in SyncEventType:
            assert isinstance(member.value, str)

    def test_str_subtype_serializes_directly(self) -> None:
        import json

        # str Enum 이므로 json.dumps 없이 value로 직렬화 가능
        assert json.dumps(SyncEventType.SYMBOL_ACTIVE_CHANGED.value) == '"SYMBOL_ACTIVE_CHANGED"'

    def test_known_values(self) -> None:
        assert SyncEventType.STRATEGY_PARAMS_CHANGED.value == "STRATEGY_PARAMS_CHANGED"
        assert SyncEventType.STRATEGY_TIMEFRAME_CHANGED.value == "STRATEGY_TIMEFRAME_CHANGED"
        assert SyncEventType.SYMBOL_ACTIVE_CHANGED.value == "SYMBOL_ACTIVE_CHANGED"
        assert SyncEventType.SYMBOL_STRATEGY_MAPPING_CHANGED.value == "SYMBOL_STRATEGY_MAPPING_CHANGED"
        assert SyncEventType.SYMBOL_RISK_CHANGED.value == "SYMBOL_RISK_CHANGED"
        # v0.4.0 추가
        assert SyncEventType.SYMBOL_COLLECTION_LINKED.value == "SYMBOL_COLLECTION_LINKED"
        # v0.5.0 추가
        assert SyncEventType.COLLECTION_TARGET_CHANGED.value == "COLLECTION_TARGET_CHANGED"

    def test_roundtrip_from_string(self) -> None:
        assert SyncEventType("SYMBOL_ACTIVE_CHANGED") is SyncEventType.SYMBOL_ACTIVE_CHANGED
        assert (
            SyncEventType("SYMBOL_COLLECTION_LINKED")
            is SyncEventType.SYMBOL_COLLECTION_LINKED
        )
        # v0.5.0
        assert (
            SyncEventType("COLLECTION_TARGET_CHANGED")
            is SyncEventType.COLLECTION_TARGET_CHANGED
        )


class TestTargetType:
    def test_count_is_8(self) -> None:
        # len(Enum) 은 unique value 기준 — alias 는 동일 member 로 카운트.
        # v0.3.0: STRATEGIES, STRATEGY_TIMEFRAMES, TRADING_SYMBOLS, SYMBOLS,
        #         SYMBOL_RISK_CONFIG, STRATEGY_SYMBOL_MAPPING, STRATEGY_EXCHANGE_SYMBOL
        #         → 7 unique.
        # v0.4.0: COLLECTION_TARGETS 추가 → 8 unique.
        # (BACKTEST_STRATEGY, STRATEGY_TIMEFRAME_CONFIG 는 alias → 카운트 미포함)
        assert len(TargetType) == 8

    def test_current_values_match_table_names(self) -> None:
        # 현행 (renamed, v0.3.0+) — enum value == 실제 DB 테이블명
        assert TargetType.STRATEGIES.value == "strategies"
        assert TargetType.STRATEGY_TIMEFRAMES.value == "strategy_timeframes"
        assert TargetType.TRADING_SYMBOLS.value == "trading_symbols"
        assert TargetType.SYMBOLS.value == "symbols"
        assert TargetType.SYMBOL_RISK_CONFIG.value == "symbol_risk_config"
        assert TargetType.STRATEGY_SYMBOL_MAPPING.value == "strategy_symbol_mapping"
        # v0.4.0 추가
        assert TargetType.COLLECTION_TARGETS.value == "collection_targets"

    def test_deprecated_aliases_preserved(self) -> None:
        # 하위호환용 alias — v0.3.0 에서 deprecated 되었지만 Step 4 까지 유지.
        # alias 는 현행 member 와 동일 객체여야 한다.
        assert TargetType.BACKTEST_STRATEGY is TargetType.STRATEGIES
        assert TargetType.STRATEGY_TIMEFRAME_CONFIG is TargetType.STRATEGY_TIMEFRAMES
        # STRATEGY_EXCHANGE_SYMBOL 은 rename 대상 — Step 4 에서 제거 예정 하지만
        # 현재는 별도 값 유지.
        assert TargetType.STRATEGY_EXCHANGE_SYMBOL.value == "strategy_exchange_symbol"

    def test_roundtrip_from_string(self) -> None:
        assert TargetType("trading_symbols") is TargetType.TRADING_SYMBOLS
        assert TargetType("strategy_exchange_symbol") is TargetType.STRATEGY_EXCHANGE_SYMBOL
        # v0.4.0
        assert TargetType("collection_targets") is TargetType.COLLECTION_TARGETS


class TestSyncAction:
    def test_count_is_3(self) -> None:
        assert len(SyncAction) == 3

    def test_known_values(self) -> None:
        assert SyncAction.INSERT.value == "INSERT"
        assert SyncAction.UPDATE.value == "UPDATE"
        assert SyncAction.DELETE.value == "DELETE"

    def test_action_whitelist_consistency(self) -> None:
        # SyncAction enum과 validators._ACTION_WHITELIST 값 동기화 검증
        from py_sync_contracts.validators import _ACTION_WHITELIST

        action_enum_values = {a.value for a in SyncAction}
        assert action_enum_values == _ACTION_WHITELIST

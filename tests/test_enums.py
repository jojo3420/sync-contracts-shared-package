"""test_enums.py — SyncEventType, TargetType, SyncAction enum 완전성 테스트."""
from __future__ import annotations

from py_sync_contracts import SyncAction, SyncEventType, TargetType


class TestSyncEventType:
    def test_count_is_5(self) -> None:
        # Plan §2.3 — 5종 고정 (v0.1.0). 추가 시 minor bump 필요.
        assert len(SyncEventType) == 5

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

    def test_roundtrip_from_string(self) -> None:
        assert SyncEventType("SYMBOL_ACTIVE_CHANGED") is SyncEventType.SYMBOL_ACTIVE_CHANGED


class TestTargetType:
    def test_count_is_4(self) -> None:
        # Plan §2.4 — 4종 고정 (v0.1.0).
        assert len(TargetType) == 4

    def test_values_match_table_names(self) -> None:
        # enum value == 실제 DB 테이블명 1:1 대응
        assert TargetType.BACKTEST_STRATEGY.value == "backtest_strategy"
        assert TargetType.STRATEGY_TIMEFRAME_CONFIG.value == "strategy_timeframe_config"
        assert TargetType.TRADING_SYMBOLS.value == "trading_symbols"
        assert TargetType.SYMBOL_RISK_CONFIG.value == "symbol_risk_config"

    def test_roundtrip_from_string(self) -> None:
        assert TargetType("trading_symbols") is TargetType.TRADING_SYMBOLS


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

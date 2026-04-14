"""test_payload.py — parse_payload() 단위 테스트.

py-algo test_events.py 에서 이식. import path 만 변경 (my_app.sync.events → py_sync_contracts).
"""
from __future__ import annotations

import json

import pytest

from py_sync_contracts import (
    PayloadError,
    SyncEventType,
    SyncPayload,
    TargetType,
    parse_payload,
)


def _valid_payload(**overrides) -> dict:  # type: ignore[type-arg]
    base = {
        "event_id": 1234,
        "event_type": "SYMBOL_ACTIVE_CHANGED",
        "target_type": "trading_symbols",
        "target_id": "42",
        "sync_version": 17,
        "action": "UPDATE",
        "actor": "joel.noru",
        "timestamp": "2026-04-13T12:34:56.123+00:00",
    }
    base.update(overrides)
    return base


def _raw(payload: dict) -> bytes:  # type: ignore[type-arg]
    return json.dumps(payload).encode("utf-8")


class TestChannelConstant:
    def test_channel_is_publisher_contract(self) -> None:
        from py_sync_contracts import SYNC_CHANNEL

        # wire contract — 절대 변경 금지
        assert SYNC_CHANNEL == "strategy_symbol_sync"


class TestParsePayloadHappyPath:
    def test_valid_bytes(self) -> None:
        result = parse_payload(_raw(_valid_payload()))
        assert isinstance(result, SyncPayload)
        assert result.event_id == 1234
        assert result.event_type is SyncEventType.SYMBOL_ACTIVE_CHANGED
        assert result.target_type is TargetType.TRADING_SYMBOLS
        assert result.target_id == "42"
        assert result.sync_version == 17
        assert result.action == "UPDATE"
        assert result.actor == "joel.noru"

    def test_valid_str(self) -> None:
        result = parse_payload(json.dumps(_valid_payload()))
        assert result.event_id == 1234

    def test_valid_bytearray(self) -> None:
        result = parse_payload(bytearray(_raw(_valid_payload())))
        assert result.event_id == 1234

    def test_payload_is_frozen(self) -> None:
        result = parse_payload(_raw(_valid_payload()))
        with pytest.raises((AttributeError, Exception)):
            result.event_id = 99  # type: ignore[misc]

    def test_int_target_id_is_coerced_to_str(self) -> None:
        result = parse_payload(_raw(_valid_payload(target_id=42)))
        assert result.target_id == "42"

    def test_composite_target_id(self) -> None:
        result = parse_payload(_raw(_valid_payload(target_id="BTCUSDT:bitget:1h")))
        assert result.target_id == "BTCUSDT:bitget:1h"


class TestParsePayloadInvalidJSON:
    def test_invalid_json(self) -> None:
        with pytest.raises(PayloadError, match="invalid JSON"):
            parse_payload(b"{not json")

    def test_json_array_not_dict(self) -> None:
        with pytest.raises(PayloadError, match="must be a JSON object"):
            parse_payload(b"[1,2,3]")

    def test_json_string_not_dict(self) -> None:
        with pytest.raises(PayloadError, match="must be a JSON object"):
            parse_payload(b'"hello"')


class TestParsePayloadMissingFields:
    @pytest.mark.parametrize(
        "missing_field",
        [
            "event_id",
            "event_type",
            "target_type",
            "target_id",
            "sync_version",
            "action",
            "actor",
            "timestamp",
        ],
    )
    def test_missing_required_field(self, missing_field: str) -> None:
        payload = _valid_payload()
        del payload[missing_field]
        with pytest.raises(PayloadError, match="missing fields"):
            parse_payload(_raw(payload))


class TestParsePayloadUnknownEnum:
    def test_unknown_event_type(self) -> None:
        # 미래 버전 이벤트 → PayloadError 로 분기, 프로세스 생존
        with pytest.raises(PayloadError, match="unknown event_type"):
            parse_payload(_raw(_valid_payload(event_type="FUTURE_EVENT")))

    def test_unknown_target_type(self) -> None:
        with pytest.raises(PayloadError, match="unknown target_type"):
            parse_payload(_raw(_valid_payload(target_type="unknown_table")))

    def test_unknown_action(self) -> None:
        with pytest.raises(PayloadError, match="unknown action"):
            parse_payload(_raw(_valid_payload(action="TRUNCATE")))


class TestParsePayloadTypeValidation:
    def test_event_id_not_int(self) -> None:
        with pytest.raises(PayloadError, match="event_id"):
            parse_payload(_raw(_valid_payload(event_id="123")))

    def test_event_id_negative(self) -> None:
        with pytest.raises(PayloadError, match="event_id"):
            parse_payload(_raw(_valid_payload(event_id=-1)))

    def test_event_id_bool_rejected(self) -> None:
        # bool 은 int 의 서브타입이지만 의미상 부정확 → 거부
        with pytest.raises(PayloadError, match="event_id"):
            parse_payload(_raw(_valid_payload(event_id=True)))

    def test_sync_version_negative(self) -> None:
        with pytest.raises(PayloadError, match="sync_version"):
            parse_payload(_raw(_valid_payload(sync_version=-5)))

    def test_sync_version_not_int(self) -> None:
        with pytest.raises(PayloadError, match="sync_version"):
            parse_payload(_raw(_valid_payload(sync_version=1.5)))

    def test_empty_target_id(self) -> None:
        with pytest.raises(PayloadError, match="target_id"):
            parse_payload(_raw(_valid_payload(target_id="")))

    def test_null_target_id(self) -> None:
        with pytest.raises(PayloadError, match="target_id"):
            parse_payload(_raw(_valid_payload(target_id=None)))


class TestParsePayloadActorValidation:
    @pytest.mark.parametrize(
        "actor",
        [
            "joel.noru",
            "admin",
            "user_01",
            "A-B.C_1",
            "x" * 64,  # max length
        ],
    )
    def test_valid_actors(self, actor: str) -> None:
        result = parse_payload(_raw(_valid_payload(actor=actor)))
        assert result.actor == actor

    @pytest.mark.parametrize(
        "actor",
        [
            "",
            "x" * 65,  # too long
            "joel noru",  # space
            "joel@noru",  # @
            "조엘",  # non-ascii
            "joel/noru",
        ],
    )
    def test_invalid_actors(self, actor: str) -> None:
        with pytest.raises(PayloadError, match="invalid actor"):
            parse_payload(_raw(_valid_payload(actor=actor)))

    def test_actor_not_string(self) -> None:
        with pytest.raises(PayloadError, match="invalid actor"):
            parse_payload(_raw(_valid_payload(actor=123)))


class TestParsePayloadTimestampValidation:
    def test_valid_timestamp_kept_as_string(self) -> None:
        result = parse_payload(
            _raw(_valid_payload(timestamp="2026-04-13T12:34:56.123+00:00"))
        )
        assert result.timestamp == "2026-04-13T12:34:56.123+00:00"

    def test_empty_timestamp(self) -> None:
        with pytest.raises(PayloadError, match="timestamp"):
            parse_payload(_raw(_valid_payload(timestamp="")))

    def test_timestamp_not_string(self) -> None:
        with pytest.raises(PayloadError, match="timestamp"):
            parse_payload(_raw(_valid_payload(timestamp=1234567890)))

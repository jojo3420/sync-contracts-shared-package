"""test_publisher.py — publish_sync_event() 직렬화 및 wire-compatibility 테스트.

fakeredis 사용 — redis-py 실제 연결 불필요.
pip install fakeredis 필요 (dev extra 포함).
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, call

import pytest

from py_sync_contracts import (
    SYNC_CHANNEL,
    SyncEventType,
    SyncPayload,
    TargetType,
    parse_payload,
    publish_sync_event,
)


def _make_payload(**overrides) -> SyncPayload:  # type: ignore[type-arg]
    defaults = dict(
        event_id=999,
        event_type=SyncEventType.SYMBOL_ACTIVE_CHANGED,
        target_type=TargetType.TRADING_SYMBOLS,
        target_id="42",
        sync_version=5,
        action="UPDATE",
        actor="admin",
        timestamp="2026-04-14T00:00:00.000+00:00",
    )
    defaults.update(overrides)
    return SyncPayload(**defaults)  # type: ignore[arg-type]


class TestPublishSyncEvent:
    def test_publishes_to_correct_channel(self) -> None:
        mock_redis = MagicMock()
        mock_redis.publish.return_value = 1

        publish_sync_event(mock_redis, _make_payload())

        args = mock_redis.publish.call_args
        channel = args[0][0]
        assert channel == SYNC_CHANNEL

    def test_returns_subscriber_count(self) -> None:
        mock_redis = MagicMock()
        mock_redis.publish.return_value = 3

        result = publish_sync_event(mock_redis, _make_payload())
        assert result == 3

    def test_returns_int(self) -> None:
        mock_redis = MagicMock()
        mock_redis.publish.return_value = 0

        result = publish_sync_event(mock_redis, _make_payload())
        assert isinstance(result, int)

    def test_serialized_json_is_valid(self) -> None:
        mock_redis = MagicMock()
        mock_redis.publish.return_value = 1

        publish_sync_event(mock_redis, _make_payload())

        json_str = mock_redis.publish.call_args[0][1]
        data = json.loads(json_str)
        assert isinstance(data, dict)

    def test_enum_values_serialized_as_strings(self) -> None:
        mock_redis = MagicMock()
        mock_redis.publish.return_value = 1

        publish_sync_event(mock_redis, _make_payload())

        json_str = mock_redis.publish.call_args[0][1]
        data = json.loads(json_str)
        assert data["event_type"] == "SYMBOL_ACTIVE_CHANGED"
        assert data["target_type"] == "trading_symbols"

    def test_all_required_fields_present(self) -> None:
        mock_redis = MagicMock()
        mock_redis.publish.return_value = 1

        publish_sync_event(mock_redis, _make_payload())

        json_str = mock_redis.publish.call_args[0][1]
        data = json.loads(json_str)
        required = {"event_id", "event_type", "target_type", "target_id",
                    "sync_version", "action", "actor", "timestamp"}
        assert required.issubset(data.keys())

    def test_wire_compatible_roundtrip(self) -> None:
        """publish_sync_event → parse_payload 왕복 테스트 (wire compatibility 핵심)."""
        mock_redis = MagicMock()
        mock_redis.publish.return_value = 1

        original = _make_payload()
        publish_sync_event(mock_redis, original)

        published_bytes = mock_redis.publish.call_args[0][1].encode("utf-8")
        recovered = parse_payload(published_bytes)

        assert recovered.event_id == original.event_id
        assert recovered.event_type is original.event_type
        assert recovered.target_type is original.target_type
        assert recovered.target_id == original.target_id
        assert recovered.sync_version == original.sync_version
        assert recovered.action == original.action
        assert recovered.actor == original.actor
        assert recovered.timestamp == original.timestamp

    @pytest.mark.parametrize("event_type", list(SyncEventType))
    def test_all_event_types_roundtrip(self, event_type: SyncEventType) -> None:
        mock_redis = MagicMock()
        mock_redis.publish.return_value = 1

        payload = _make_payload(event_type=event_type)
        publish_sync_event(mock_redis, payload)

        published_bytes = mock_redis.publish.call_args[0][1].encode("utf-8")
        recovered = parse_payload(published_bytes)
        assert recovered.event_type is event_type

    @pytest.mark.parametrize("target_type", list(TargetType))
    def test_all_target_types_roundtrip(self, target_type: TargetType) -> None:
        mock_redis = MagicMock()
        mock_redis.publish.return_value = 1

        payload = _make_payload(target_type=target_type)
        publish_sync_event(mock_redis, payload)

        published_bytes = mock_redis.publish.call_args[0][1].encode("utf-8")
        recovered = parse_payload(published_bytes)
        assert recovered.target_type is target_type

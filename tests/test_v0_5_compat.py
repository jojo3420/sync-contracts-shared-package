"""v0.5.0 호환성 및 graceful-ignore 계약 테스트.

timeseries-rca-auto-sync Design Ref: §4.2 event schema, §4.3 event contract,
NFR-04 (3-repo 버전 호환 — v0.4.0 수신자가 v0.5.0 메시지를 gracefully ignore).

graceful-ignore 계약:
    - v0.5.0 파서(현재)는 COLLECTION_TARGET_CHANGED 를 정상 파싱.
    - 구독자는 parse_payload 에서 PayloadError 발생 시 WARNING 로그 후 다음 메시지로 진행 (crash 금지).
    - 알 수 없는 event_type 수신 시 PayloadError 가 raise 되어야만 구독자가 catch 가능.
      (이 테스트가 회귀 방지장치 — parser 가 silently pass 하면 unknown event 가 처리 로직에 유입됨.)
"""
from __future__ import annotations

import json

import pytest

from py_sync_contracts import PayloadError, SyncEventType, TargetType, parse_payload


def _base_payload(**overrides: object) -> bytes:
    """v0.5.0 COLLECTION_TARGET_CHANGED 표준 페이로드 생성."""
    data: dict[str, object] = {
        "event_id": 12345,
        "event_type": "COLLECTION_TARGET_CHANGED",
        "target_type": "collection_targets",
        "target_id": "42",
        "sync_version": 47,
        "action": "INSERT",
        "actor": "admin_joel.silver",
        "timestamp": "2026-04-18T03:34:56Z",
    }
    data.update(overrides)
    return json.dumps(data).encode("utf-8")


class TestCollectionTargetChangedPayload:
    """v0.5.0 신규 event_type — Publisher→Subscriber 정방향 파싱."""

    def test_parses_insert_action(self) -> None:
        payload = parse_payload(_base_payload(action="INSERT"))
        assert payload.event_type is SyncEventType.COLLECTION_TARGET_CHANGED
        assert payload.target_type is TargetType.COLLECTION_TARGETS
        assert payload.action == "INSERT"
        assert payload.sync_version == 47

    def test_parses_update_action(self) -> None:
        payload = parse_payload(_base_payload(action="UPDATE"))
        assert payload.action == "UPDATE"

    def test_parses_delete_action(self) -> None:
        payload = parse_payload(_base_payload(action="DELETE"))
        assert payload.action == "DELETE"

    def test_str_roundtrip_preserves_event_type(self) -> None:
        # str Enum — Redis 로 다시 직렬화해도 동일
        payload = parse_payload(_base_payload())
        assert payload.event_type.value == "COLLECTION_TARGET_CHANGED"


class TestGracefulIgnoreContract:
    """v0.4.0 구독자가 v0.5.0 이벤트를 수신할 때의 계약 회귀 방지.

    실제 v0.4.0 파서는 COLLECTION_TARGET_CHANGED 를 unknown event_type 으로
    인식해 PayloadError 를 raise 한다. 구독 루프는 이 예외를 catch 후 skip.

    현재 v0.5.0 파서에서는 "알 수 없는" event_type(가짜)을 보내 동일한 계약을 검증.
    """

    def test_unknown_event_type_raises_payload_error(self) -> None:
        """parser 가 unknown event_type 에 대해 PayloadError 를 raise 해야 한다.
        구독자가 catch 하려면 예외 클래스가 일관되어야 한다.
        """
        raw = _base_payload(event_type="FUTURE_EVENT_NOT_YET_EXISTS_v0_9")
        with pytest.raises(PayloadError) as exc_info:
            parse_payload(raw)
        assert "unknown event_type" in str(exc_info.value)

    def test_unknown_event_type_error_is_catchable_by_subscriber(self) -> None:
        """구독 루프 pattern — try/except PayloadError 로 잡으면 프로세스 지속."""
        raw = _base_payload(event_type="HYPOTHETICAL_V10_EVENT")
        processed = False
        try:
            parse_payload(raw)
            processed = True
        except PayloadError:
            # 구독자가 해야 할 처리: WARNING 로그 + continue
            pass
        assert processed is False  # parse 단계에서 차단됨
        # 예외 이후에도 다음 메시지 파싱 가능해야 함
        next_payload = parse_payload(_base_payload())
        assert next_payload.event_type is SyncEventType.COLLECTION_TARGET_CHANGED

    def test_payload_error_is_not_generic_exception(self) -> None:
        """PayloadError 가 ValueError 하위 클래스 — 구독자가 broad except Exception
        없이 명시적 except 로 격리 가능해야 한다."""
        assert issubclass(PayloadError, ValueError)

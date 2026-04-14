"""Sync 이벤트 페이로드 스키마 및 파서.

py-algo(Subscriber) 측의 canonical 구현을 이식.
Publisher(trading-admin-dashboard)와 Subscriber(py-algo) 양쪽이
이 모듈을 공유함으로써 parse 계약의 단일 출처(SSoT)를 보장한다.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from py_sync_contracts.enums import SyncEventType, TargetType
from py_sync_contracts.validators import _ACTION_WHITELIST, validate_actor

_REQUIRED_FIELDS: tuple[str, ...] = (
    "event_id",
    "event_type",
    "target_type",
    "target_id",
    "sync_version",
    "action",
    "actor",
    "timestamp",
)


@dataclass(frozen=True)
class SyncPayload:
    """파싱·검증 통과한 Publisher 이벤트 (불변).

    frozen=True: 멀티스레드 환경에서 안전하게 공유 가능.
    """

    event_id: int
    event_type: SyncEventType
    target_type: TargetType
    target_id: str
    sync_version: int
    action: str  # v0.2.0에서 SyncAction으로 강화 예정
    actor: str
    timestamp: str  # ISO-8601 UTC 원문 — 필요 시 handler 에서 추가 파싱


class PayloadError(ValueError):
    """페이로드 파싱·검증 실패.

    구독 루프는 이 예외를 잡아 WARNING 로그로 기록하고 다음 메시지로 넘어가야 한다.
    프로세스를 죽이지 않는다 — 미래 버전 이벤트 수신 시 생존 보장.
    """


def _coerce_raw(raw: bytes | str | bytearray | memoryview) -> str:
    """raw 입력을 str 로 정규화."""
    if isinstance(raw, (bytes, bytearray)):
        return bytes(raw).decode("utf-8", errors="strict")
    if isinstance(raw, memoryview):
        return bytes(raw).decode("utf-8", errors="strict")
    if isinstance(raw, str):
        return raw
    raise PayloadError(f"unsupported raw type: {type(raw).__name__}")


def parse_payload(raw: bytes | str | bytearray | memoryview) -> SyncPayload:
    """Publisher 이벤트 JSON을 검증 후 SyncPayload로 변환.

    Args:
        raw: Redis에서 수신한 원문 (bytes, str, bytearray, memoryview 모두 허용).

    Returns:
        검증된 SyncPayload (frozen dataclass).

    Raises:
        PayloadError: JSON 파싱 실패, 필수 필드 누락, 알 수 없는 enum,
            타입 불일치, actor 포맷 위반 등 모든 검증 실패.
    """
    try:
        text = _coerce_raw(raw)
    except UnicodeDecodeError as exc:
        raise PayloadError(f"utf-8 decode error: {exc}") from exc

    try:
        data: Any = json.loads(text)
    except json.JSONDecodeError as exc:
        raise PayloadError(f"invalid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise PayloadError(f"payload must be a JSON object, got {type(data).__name__}")

    missing = [f for f in _REQUIRED_FIELDS if f not in data]
    if missing:
        raise PayloadError(f"missing fields: {missing}")

    # event_type / target_type enum whitelist 검증
    try:
        event_type = SyncEventType(data["event_type"])
    except ValueError as exc:
        raise PayloadError(f"unknown event_type: {data['event_type']!r}") from exc
    try:
        target_type = TargetType(data["target_type"])
    except ValueError as exc:
        raise PayloadError(f"unknown target_type: {data['target_type']!r}") from exc

    action = data["action"]
    if not isinstance(action, str) or action not in _ACTION_WHITELIST:
        raise PayloadError(f"unknown action: {action!r}")

    try:
        actor = validate_actor(data["actor"])
    except ValueError as exc:
        raise PayloadError(str(exc)) from exc

    event_id = data["event_id"]
    if not isinstance(event_id, int) or isinstance(event_id, bool) or event_id < 0:
        raise PayloadError(f"event_id must be non-negative int, got {event_id!r}")

    sync_version = data["sync_version"]
    if (
        not isinstance(sync_version, int)
        or isinstance(sync_version, bool)
        or sync_version < 0
    ):
        raise PayloadError(
            f"sync_version must be non-negative int, got {sync_version!r}"
        )

    target_id_raw = data["target_id"]
    # 계약상 문자열이지만 publisher 가 int로 보낼 수도 있으므로 str 강제
    if isinstance(target_id_raw, bool) or target_id_raw is None:
        raise PayloadError(f"invalid target_id: {target_id_raw!r}")
    target_id = str(target_id_raw)
    if not target_id:
        raise PayloadError("target_id must be non-empty")

    timestamp_raw = data["timestamp"]
    if not isinstance(timestamp_raw, str) or not timestamp_raw:
        raise PayloadError(f"invalid timestamp: {timestamp_raw!r}")

    return SyncPayload(
        event_id=event_id,
        event_type=event_type,
        target_type=target_type,
        target_id=target_id,
        sync_version=sync_version,
        action=action,
        actor=actor,
        timestamp=timestamp_raw,
    )

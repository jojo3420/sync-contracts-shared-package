"""py_sync_contracts — strategy_symbol_sync 채널 계약 패키지.

Publisher(trading-admin-dashboard)와 Subscriber(py-algo-stragegy-system-v1)가
공유하는 단일 출처(SSoT):
  - Redis 채널명 (SYNC_CHANNEL)
  - 이벤트 타입 enum (SyncEventType, TargetType, SyncAction)
  - 페이로드 스키마 (SyncPayload)
  - 파서 (parse_payload)
  - Publisher helper (publish_sync_event)

빠른 시작:
    # Subscriber 측
    from py_sync_contracts import SYNC_CHANNEL, parse_payload, PayloadError

    # Publisher 측 (pip install 'py-sync-contracts[publisher]' 필요)
    from py_sync_contracts import publish_sync_event, SyncPayload

버전 규칙:
    - minor bump: 새 enum 값·필드 추가 (하위 호환)
    - major bump: enum 삭제·필드 제거·채널명 변경 (파괴적 변경)
"""
from __future__ import annotations

from py_sync_contracts.channels import SYNC_CHANNEL
from py_sync_contracts.enums import SyncAction, SyncEventType, TargetType
from py_sync_contracts.payload import PayloadError, SyncPayload, parse_payload
from py_sync_contracts.publisher import publish_sync_event
from py_sync_contracts.strategy_requirements import calculate_required_candles
from py_sync_contracts.validators import ACTOR_REGEX

# pyproject.toml 과 반드시 일치시킨다. 드리프트 방지.
__version__: str = "0.4.0"

__all__ = [
    "__version__",
    # 채널
    "SYNC_CHANNEL",
    # enum
    "SyncEventType",
    "TargetType",
    "SyncAction",
    # 페이로드
    "SyncPayload",
    "parse_payload",
    "PayloadError",
    # publisher helper
    "publish_sync_event",
    # validator
    "ACTOR_REGEX",
    # strategy requirements (v0.4.0)
    "calculate_required_candles",
]

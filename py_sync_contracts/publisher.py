"""Publisher helper 모듈.

SyncPayload를 SYNC_CHANNEL로 JSON 직렬화하여 Redis PUBLISH를 수행한다.
redis-py 의존성은 optional — pip install 'py-sync-contracts[publisher]' 필요.

사용 예:
    from py_sync_contracts import publish_sync_event, SyncPayload
    count = publish_sync_event(redis_client, payload)
"""
from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from py_sync_contracts.channels import SYNC_CHANNEL
from py_sync_contracts.payload import SyncPayload

if TYPE_CHECKING:
    # 타입 검사 시에만 import — 런타임에는 redis 없어도 동작
    import redis as _redis_module


def publish_sync_event(
    redis_client: Any,
    payload: SyncPayload,
) -> int:
    """SyncPayload를 SYNC_CHANNEL에 JSON으로 발행.

    serialize 방식이 parse_payload()와 wire-compatible 하도록 설계됨.
    즉, publish_sync_event()로 발행한 메시지를 parse_payload()로 역파싱하면
    원본 SyncPayload와 동일한 결과를 낸다.

    Args:
        redis_client: redis.Redis 인스턴스 (또는 .publish 메서드를 가진 객체).
            pip install 'py-sync-contracts[publisher]' 로 redis-py 설치 필요.
        payload: 발행할 SyncPayload (frozen dataclass).

    Returns:
        int: 메시지를 수신한 구독자 수 (redis.publish 반환값).

    Raises:
        ImportError: redis-py 미설치 시 redis_client.publish 호출 단계에서 발생.
        redis.RedisError: Redis 연결/인증 오류 (redis-py 예외 그대로 전파).
    """
    data = {
        "event_id": payload.event_id,
        "event_type": payload.event_type.value,
        "target_type": payload.target_type.value,
        "target_id": payload.target_id,
        "sync_version": payload.sync_version,
        "action": payload.action,
        "actor": payload.actor,
        "timestamp": payload.timestamp,
    }
    result = redis_client.publish(SYNC_CHANNEL, json.dumps(data, ensure_ascii=False))
    return int(result)

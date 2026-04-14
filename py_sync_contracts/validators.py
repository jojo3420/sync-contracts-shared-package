"""actor 필드 검증 모듈.

ACTOR_REGEX를 public 상수로 노출하여 소비자 프로젝트에서 재사용 가능하도록 한다.
"""
from __future__ import annotations

import re
from typing import Final

# actor 필드 허용 패턴 (pub: public constant)
ACTOR_REGEX: Final[str] = r"^[A-Za-z0-9._\-]{1,64}$"

# 내부 컴파일 캐시 — 패키지 import 시 1회만 컴파일
_ACTOR_PATTERN: Final[re.Pattern[str]] = re.compile(ACTOR_REGEX)

# action 허용값 — 내부 사용 (SyncAction enum과 동기화 유지)
_ACTION_WHITELIST: Final[frozenset[str]] = frozenset({"INSERT", "UPDATE", "DELETE"})


def validate_actor(actor: object) -> str:
    """actor 필드 유효성 검증.

    Args:
        actor: 검증할 값 (str 이어야 함).

    Returns:
        검증 통과한 actor 문자열.

    Raises:
        ValueError: actor가 str 이 아니거나 ACTOR_REGEX와 불일치.
    """
    if not isinstance(actor, str) or not _ACTOR_PATTERN.match(actor):
        raise ValueError(f"invalid actor: {actor!r}")
    return actor

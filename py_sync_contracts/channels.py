"""채널 상수 모듈.

Redis pub/sub 채널명을 단일 출처(SSoT)로 정의한다.
변경 시 반드시 major version bump 필요 (wire contract).
"""
from __future__ import annotations

from typing import Final

# Redis 채널 상수 — Publisher/Subscriber 계약. 절대 변경 금지.
SYNC_CHANNEL: Final[str] = "strategy_symbol_sync"

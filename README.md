# py-sync-contracts

`strategy_symbol_sync` Redis 채널의 Publisher/Subscriber 계약 패키지.

`trading-admin-dashboard`(Publisher)와 `py-algo-stragegy-system-v1`(Subscriber) 양쪽이
이 패키지를 공유 의존성으로 사용해 **채널명·enum·payload 스키마의 단일 출처(SSoT)**를 보장한다.

---

## 설치

### Subscriber (py-algo-stragegy-system-v1)

```bash
pip install "py-sync-contracts @ git+https://github.com/jojo3420/sync-contracts-shared-package.git@v0.1.0"
```

### Publisher (trading-admin-dashboard)

```bash
# publisher helper 포함 설치 (redis-py optional extra)
pip install "py-sync-contracts[publisher] @ git+https://github.com/jojo3420/sync-contracts-shared-package.git@v0.1.0"
```

---

## 사용법

### Subscriber 측 (py-algo)

```python
from py_sync_contracts import (
    SYNC_CHANNEL,
    SyncPayload,
    parse_payload,
    PayloadError,
    SyncEventType,
    TargetType,
)

# Redis pub/sub 구독
pubsub.subscribe(SYNC_CHANNEL)

for msg in pubsub.listen():
    if msg["type"] != "message":
        continue
    try:
        payload: SyncPayload = parse_payload(msg["data"])
    except PayloadError as exc:
        logger.warning(f"parse error: {exc}")
        continue

    if payload.target_type is TargetType.TRADING_SYMBOLS:
        handle_symbol_change(payload)
```

### Publisher 측 (trading-admin-dashboard)

```python
import redis
from py_sync_contracts import SyncPayload, SyncEventType, TargetType, publish_sync_event

r = redis.Redis(host="localhost", port=6379, db=1)

payload = SyncPayload(
    event_id=1001,
    event_type=SyncEventType.SYMBOL_ACTIVE_CHANGED,
    target_type=TargetType.TRADING_SYMBOLS,
    target_id="42",
    sync_version=18,
    action="UPDATE",
    actor="admin.user",
    timestamp="2026-04-14T09:00:00.000+00:00",
)

subscribers_count = publish_sync_event(r, payload)
print(f"수신자 수: {subscribers_count}")
```

---

## 패키지 구조

```
py_sync_contracts/
├── channels.py     # SYNC_CHANNEL 상수
├── enums.py        # SyncEventType, TargetType, SyncAction
├── validators.py   # ACTOR_REGEX, validate_actor()
├── payload.py      # SyncPayload, parse_payload(), PayloadError
├── publisher.py    # publish_sync_event() — [publisher] extra 필요
└── __init__.py     # Public API 전체 re-export
```

---

## 버전 규칙 (SemVer)

| 변경 종류 | Bump |
|----------|------|
| 새 enum 값 추가, 새 필드 추가 (하위 호환) | `minor` |
| 채널명 변경, enum 값 삭제, 필드 제거/타입 변경 | `major` |
| 버그 수정, 문서 수정, 테스트 추가 | `patch` |

> **양쪽 동시 배포 규칙**: major bump 시 Publisher(admin)와 Subscriber(py-algo) 모두 같은 버전으로 동시 업그레이드. minor/patch는 독립 업그레이드 가능.

---

## 버전 업그레이드 절차

1. `pyproject.toml` → `version` 변경
2. `py_sync_contracts/__init__.py` → `__version__` 변경
3. PR → main merge
4. `git tag v{version}` + `git push origin v{version}`
5. CI 자동 실행 (pytest + mypy + version 일치 확인)
6. 양쪽 프로젝트 requirements 업데이트 + 테스트 → 동시 PR

---

## 개발 환경 설정

```bash
git clone https://github.com/jojo3420/sync-contracts-shared-package.git
cd sync-contracts-shared-package
pip install -e ".[dev]"
pytest
mypy py_sync_contracts --strict
```

---

## trading-admin-dashboard 마이그레이션 가이드

### Step 1: 의존성 추가

`requirements.txt` (또는 `conda/environment.yml`) 에 추가:

```
py-sync-contracts[publisher] @ git+https://github.com/jojo3420/sync-contracts-shared-package.git@v0.1.0
```

### Step 2: 기존 `sync_events.py` 삭제 및 import 교체

**삭제 대상**: `backend/app/constants/sync_events.py`

모든 import 를 교체:

```python
# BEFORE
from app.constants.sync_events import SYNC_CHANNEL, SyncEventType, TargetType

# AFTER
from py_sync_contracts import SYNC_CHANNEL, SyncEventType, TargetType
```

### Step 3: Publisher service 리팩토링

`backend/app/services/sync_publisher_service.py`:

```python
# BEFORE
import json
from app.constants.sync_events import SYNC_CHANNEL

def publish_event(redis_client, event_data: dict) -> int:
    return redis_client.publish(SYNC_CHANNEL, json.dumps(event_data))

# AFTER — SyncPayload 생성 후 helper 사용
from py_sync_contracts import SyncPayload, publish_sync_event

def publish_event(redis_client, payload: SyncPayload) -> int:
    return publish_sync_event(redis_client, payload)
```

### Step 4: 테스트 확인

```bash
cd trading-admin-dashboard/backend
pytest
```

### Step 5: 기동 시 버전 검증 (권장)

```python
# main.py 또는 startup 이벤트에 추가
import py_sync_contracts
logger.info(f"[contracts] py-sync-contracts v{py_sync_contracts.__version__}")
assert py_sync_contracts.__version__ == "0.1.0"
```

---

## 관련 프로젝트

- **Publisher**: `trading-admin-dashboard` — admin 관리 UI + Redis PUBLISH
- **Subscriber**: `py-algo-stragegy-system-v1` — Redis SUBSCRIBE + 전략 런타임 갱신

> **Contract 변경 원칙**: `SYNC_CHANNEL`, enum, `SyncPayload` 필드 변경은 **반드시 이 repo에서만** 진행한다. 각 프로젝트에서 로컬 정의를 추가하지 않는다.

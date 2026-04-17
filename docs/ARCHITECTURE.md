# Trading System — 통합 아키텍처 (SSoT)

> 3개 프로젝트 공용 단일 출처. 변경 시 모든 프로젝트 영향 → PR 리뷰 필수.
> 경로 기준: `gitroom/python/` 하위 동일 레이아웃 (dev=로컬 macOS, prod=192.168.0.92).

## 1. 프로젝트 & 역할

| 프로젝트 | 역할 | 기술 |
|---------|------|------|
| `py-algo-stragegy-system-v1` | 전략 실행, Signal 생성, Sync subscriber | Python |
| `order-interface-py-v1` | 거래소 주문 체결(Upbit/Bitget/KIS), 시계열 수집 API | Python / FastAPI |
| `trading-admin-dashboard` | 어드민 대시보드 툴 (운영/모니터링/메타정보 관리 UI), Sync publisher | FastAPI + Next.js |
| `sync-contracts-shared-package` | Enum/payload/채널 계약 패키지 (본 문서 포함) | Python lib |

## 2. 데이터 흐름

```
dashboard ──(Redis pub: strategy_symbol_sync)──▶ algo
dashboard ──(DB write: 메타 테이블)──▶ PostgreSQL ◀── algo/order (read)
algo ──(HTTP POST /signals)──▶ order ──(REST)──▶ 거래소
algo ──(DB write)──▶ signal_request
order ──(DB write)──▶ order_history
order ──(HTTP GET /candles, /ticker)──▶ algo
```

- **흐름①** 메타 동기화: dashboard가 DB 업데이트 후 Redis publish → algo가 subscribe하여 핫 리로드
- **흐름②** Signal 체결: algo가 signal_request 기록 + order-interface HTTP 호출 → 거래소 체결
- **흐름③** 시세 조회: order-interface가 수집·정규화한 시계열을 algo가 REST로 조회

## 3. 계약 (py_sync_contracts)

| 항목 | 값 | 파일 |
|------|-----|------|
| Redis 채널 | `strategy_symbol_sync` | `channels.py` (`SYNC_CHANNEL`) |
| Publisher | dashboard (단독) | — |
| Subscriber | algo | — |
| Payload | `SyncPayload` | `payload.py` |
| 이벤트 타입 (6) | `STRATEGY_PARAMS_CHANGED`, `STRATEGY_TIMEFRAME_CHANGED`, `SYMBOL_ACTIVE_CHANGED`, `SYMBOL_STRATEGY_MAPPING_CHANGED`, `SYMBOL_RISK_CHANGED`, `SYMBOL_COLLECTION_LINKED` (v0.4.0) | `enums.SyncEventType` |
| 대상 테이블 (6) | `backtest_strategy`, `strategy_timeframe_config`, `trading_symbols`, `symbol_risk_config`, `strategy_symbol_mapping` (v0.3.0), `collection_targets` (v0.4.0) | `enums.TargetType` |
| Action | `INSERT` / `UPDATE` / `DELETE` | `enums.SyncAction` |
| 공식 공유 | `calculate_required_candles(strategy_name, parameters, buffer)` — py-algo `get_required_candles` 위임 대상 (v0.4.0) | `strategy_requirements.py` |

**⚠ 미정의**: algo↔order HTTP signal payload 스키마는 아직 `py_sync_contracts`에 없음 → 계약화 필요.

## 4. 소유권 (Ownership)

> **원칙**: 쓰기 권한을 가진 프로젝트가 유일한 소유자. 타 프로젝트는 읽기 또는 API 호출로만 접근.

| 리소스 | 쓰기 | 읽기 |
|--------|------|------|
| `backtest_strategy`, `strategy_timeframe_config`, `trading_symbols`, `symbol_risk_config` | dashboard | dashboard, algo, order\* |
| `strategy_symbol_mapping` (v0.3.0 rename) | dashboard | dashboard, algo |
| `symbols` (v0.3.0 신설) | dashboard | dashboard, algo, order |
| `collection_targets` (v0.4.0, **소유권 이전**) | dashboard \*\* | dashboard, algo, order |
| `signal_request` | algo | algo, dashboard |
| `order_history` | order | order, dashboard, algo |
| Redis `strategy_symbol_sync` | dashboard (pub) | algo (sub) |
| 거래소 API Key | order | order |

\* `trading_symbols`는 order도 읽음.

\*\* **`collection_targets` 소유권 이전 (2026-04-17, symbol-mapping-auto P2/3)**
- AS-IS: py-algo 백필 job 이 is_active 토글 쓰기 수행 예정이었으나 실제 쓰기 경로 0건
- TO-BE: dashboard `StrategySymbolOrchestrator` 가 매핑 저장의 부수효과로 upsert/soft-deactivate 수행. py-algo 는 **읽기 전용** 으로 전환.
- 근거: `grep -rn "INSERT\|UPDATE.*collection_targets" py-algo-stragegy-system-v1/` → 결과 0 건 (2026-04-17 실측). 매핑 주체 = 수집 주체가 자연스러움.
- 구독 신호: py-algo 는 `SYMBOL_COLLECTION_LINKED` 이벤트로 "새 수집 타겟 생성" 을 비동기 인지 가능 (handler 구현은 P2.1 follow-up).

## 5. 버전 정책

| 변경 | bump | 릴리스 순서 |
|------|------|-------------|
| enum 값 추가 / payload optional 필드 추가 | minor | 즉시 배포 가능 |
| enum 삭제·변경 / payload 필수 필드 변경 / 채널명·테이블명 변경 | **major** | contracts → dashboard → algo → order |

## 6. 미확정 항목 (TODO)

- [ ] algo↔order signal payload 스키마를 `py_sync_contracts`로 승격
- [ ] order-interface 인증 방식 확정 (API Key / mTLS / IP 화이트리스트)
- [ ] signal_request ↔ order_history correlation id 표준화
- [ ] 장애 degradation 전략 (Redis/order/거래소 각각)
- [ ] order-interface 시계열 API 스펙 문서화

## 7. 변경 이력

| 날짜 | 변경 |
|------|------|
| 2026-04-15 | 최초 작성 — 3개 프로젝트 통합 SSoT 수립 |
| 2026-04-17 | v0.3.0: `SYMBOLS`·`STRATEGY_SYMBOL_MAPPING` TargetType 추가 (schema-normalization). v0.4.0: `calculate_required_candles` 순수함수 승격 + `SYMBOL_COLLECTION_LINKED`·`COLLECTION_TARGETS` 추가 + `collection_targets` 쓰기 소유권 py-algo → dashboard 이전 (symbol-mapping-auto P2/3 Module 5). py-algo 는 `get_required_candles` 를 sync-contracts 위임으로 전환. |

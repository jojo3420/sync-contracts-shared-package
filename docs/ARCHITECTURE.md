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
| `symbols` (v0.3.0 신설) \*\*\*\* | dashboard | dashboard, algo, order |
| `collection_targets` (v0.4.0, **소유권 이전**) \*\*\* | dashboard \*\* | dashboard, algo, order |
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

\*\*\*\* **`symbols.symbol` 표기 규칙 (Notation SSoT, 2026-04-27)**
- **저장 포맷 = CCXT 표기 (`BTC/USDT`, 슬래시 포함)**. dashboard / algo / order 모두 이 포맷을 단일 출처로 사용.
- 근거: `crypto_timeseries`, `portfolio.positions`, `signal_request`, `order_history` 등 도메인 테이블이 모두 CCXT 표기를 키로 사용하므로 마스터 테이블도 동일 표기 유지.
- **거래소 native 포맷 변환은 어댑터 경계의 책임**. 거래소별 정규화 규칙:
  - Bitget v2 mix endpoint: `symbol.replace("/", "")` → `BTCUSDT`. 슬래시 포함 시 `code:40034 "Parameter does not exist"` 거부.
  - Upbit: `BTC/USDT` → `USDT-BTC` (KRW/USDT 등 quote 우선 표기).
  - Binance: `symbol.replace("/", "")` (Bitget 과 동일).
- 어댑터(collector / order client / WebSocket subscriber 등) 는 진입에서 자가-방어 정규화를 수행해야 한다. 호출자가 어떤 포맷을 넘기든 안전하도록 Misuse-proof 설계 (senior-mindset §4 — "오용 가능한 인터페이스는 반드시 오용된다").
- **회귀 사례 (2026-04-27 prod 인시던트)**: dashboard `BitgetFundingRateCollector.fetch_history` 가 정규화 누락 → `symbols` 테이블의 `BTC/USDT` 가 그대로 Bitget v2 API 에 전달 → 활성 22 심볼 전건 400 → funding rate 적재 중단. fix: `backend/app/services/funding_rate/collector.py` 진입에 `api_symbol = symbol.replace("/", "")` 적용 (`repository.py:36` 의 기존 정규화 패턴과 대칭). 회귀 테스트: `tests/unit/services/funding_rate/test_collector.py::test_fetch_history_normalizes_ccxt_slash_symbol_to_bitget_native`.
- 신규 거래소 어댑터 추가 시 Plan/Design 체크리스트에 "심볼 표기 정규화 진입점 가드" 항목을 포함하고, 회귀 테스트로 (CCXT 입력 → native 전송) 검증을 강제한다.
- **dashboard 자세한 가드 룰 + 매핑표 + 회귀 테스트 헬퍼 (2026-04-27, exchange-adapter-symbol-guard PDCA)**:
  - 룰 (4항목 PR 체크리스트): `trading-admin-dashboard/rules/exchange-adapter.md`
  - 매핑표 (5+ 거래소 변환 함수 + 패턴 + FAQ): `trading-admin-dashboard/docs/CONVENTIONS/exchange-adapter-guard.md`
  - 회귀 테스트 헬퍼 (`assert_fetch_normalizes`): `trading-admin-dashboard/backend/tests/utils/exchange_adapter_assertions.py`
  - Phase A 점검 보고서 (5개 모듈 누락 0건): `trading-admin-dashboard/docs/03-analysis/exchange-adapter-symbol-audit.md`
  - 신규 거래소 추가 시 양 repo (sync-contracts ARCHITECTURE.md ★★★★ + dashboard 위 4개 산출물) **동시 갱신 의무**.

\*\*\* **`sync_version` 컬럼 보강 (2026-04-18, collection-targets-sync-version)**
- `TargetType` enum 에 테이블을 추가한 owner repo 는 반드시 `sync_version BIGINT NOT NULL DEFAULT 0` 컬럼을 제공해야 한다. subscriber 는 `SELECT MAX(sync_version)` (state init) + `WHERE sync_version > :last` (catchup) 프로토콜을 전 테이블에 동일하게 적용하므로, 컬럼 부재 시 `column does not exist` 런타임 에러 발생.
- v0.4.0 최초 배포 시 dashboard 측 migration 을 누락한 gap 을 2026-04-18 dashboard `backend/migrations/029_collection_targets_add_sync_version.sql` 로 해소 (idempotent `ADD COLUMN IF NOT EXISTS`).
- 향후 enum 에 테이블 추가 시 이 owner 의무를 Plan/Design 체크리스트에 반드시 포함한다.

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
| 2026-04-18 | dashboard `collection_targets` 에 `sync_version BIGINT NOT NULL DEFAULT 0` 컬럼 보강 (`backend/migrations/029_collection_targets_add_sync_version.sql`, idempotent). symbol-mapping-auto v0.4.0 에서 누락된 owner 의무 해소. §4 footnote \*\*\* 추가: "enum 에 테이블 추가 시 owner 는 sync_version 컬럼 제공 의무". py-algo / order 측 변경 없음. (collection-targets-sync-version PDCA) |
| 2026-04-27 | §4 footnote \*\*\*\* 추가: `symbols.symbol` 표기 규칙 (CCXT SSoT) + 거래소 어댑터 경계의 native 정규화 책임. 계기: prod 인시던트 — dashboard `BitgetFundingRateCollector.fetch_history` 가 슬래시 정규화 누락으로 Bitget v2 API 22 심볼 전건 400. 신규 거래소 어댑터 추가 시 정규화 가드 + 회귀 테스트 의무화. (funding-rate-bitget-symbol-fix) |
| 2026-04-27 | §4 footnote \*\*\*\* 보강: dashboard 측 가드 룰 + CONVENTIONS 매핑표 (5+ 거래소) + 회귀 테스트 헬퍼 (`assert_fetch_normalizes`) + Phase A 점검 보고서 (5개 모듈 누락 0건) cross-link. 신규 거래소 추가 시 양 repo 동시 갱신 의무 명시. (exchange-adapter-symbol-guard PDCA) |

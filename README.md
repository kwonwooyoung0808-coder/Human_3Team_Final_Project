# Policy-Aware Agent Governance Engine

LLM 기반 에이전트의 최종 응답을 정책으로 평가하고, 자동 조치(`BLOCK` / `LOG`), 감사 기록, 실행 추적, `run_id` 기반 조회를 제공하는 로컬 거버넌스 엔진 MVP입니다.

## 프로젝트 개요

이 저장소는 `governance_detailed_prd.pdf` 기준으로 재구성한 최종 PRD 기반 백엔드 뼈대입니다.
FastAPI, SQLite, SQLAlchemy, 정책 YAML 로딩, prompts 관리, workflow/interceptor 구조, 조회 API를 우선 반영했으며, 각 역할 담당의 세부 로직은 후속 통합 단계에서 확장됩니다.

## 현재 범위

현재 반영 범위:

- FastAPI REST API
- SQLite / SQLAlchemy 기반 저장 구조
- YAML 정책 로딩
- prompts 디렉터리 분리
- workflows / interceptors / handlers 구조
- run / violation / audit / trace 조회 API
- benchmarks 디렉터리 구조

## 현재 구현 상태

현재는 최종 PRD 기준 구조와 최소 실행 가능한 흐름을 우선 구성한 상태입니다.

구현 완료:

- `GET /health`
- `POST /api/v1/evaluate`
- `GET /api/v1/runs/{run_id}`
- `GET /api/v1/runs/{run_id}/trace`
- `GET /api/v1/violations`
- `GET /api/v1/audit-logs`
- 정책 YAML 3종 기본 반영
- DB 5개 테이블 구조 반영

후속 구현 예정:

- Judge Engine 고도화
- 각 역할 세부 정책 로직 확장
- 단위/통합/E2E 테스트 확장
- benchmarks 데이터셋 및 evaluator 보강

## 프로젝트 구조

```text
src/
├── main.py
├── core/
├── schemas/
├── database/
├── utils/
├── prompts/
├── engines/
├── services/
├── workflows/
│   └── interceptors/
│       └── handlers/
├── routers/
└── policies/

tests/
├── unit/
├── integration/
├── e2e/
├── fixtures/
├── fakes/
└── benchmarks/
```

## 정책 구성

- `CONTENT_001`: Content Safety Policy
- `GROUND_001`: Groundedness Policy
- `COMP_001`: Instruction Compliance Policy

## API 목록

- `GET /health`
- `POST /api/v1/evaluate`
- `GET /api/v1/runs/{run_id}`
- `GET /api/v1/runs/{run_id}/trace`
- `GET /api/v1/violations`
- `GET /api/v1/audit-logs`

## 로컬 실행 방법

```powershell
py -m pip install -r requirements.txt
py -m uvicorn src.main:app --reload --port 8001
```

Swagger 주소:

```text
http://127.0.0.1:8001/docs
```

## Docker Compose 실행

```powershell
docker compose up --build
```

Swagger 주소:

```text
http://127.0.0.1:8000/docs
```

## 테스트 실행

```powershell
py -m pytest
```

## 대표 시나리오

1. 정상 응답: 위반 없음, 원문 응답 반환
2. Content Safety 위반: `BLOCK`, fallback response 반환
3. Groundedness 부족: `LOG`, 원문 응답 유지
4. Instruction Compliance 위반: `BLOCK`, 정책 사유 기록

## 참고 사항

이 저장소는 최종 PRD 기준의 백엔드 구조와 최소 실행 가능한 흐름을 우선 반영한 상태입니다.
세부 정책 로직, Judge 고도화, 역할별 테스트는 후속 통합 단계에서 확장됩니다.

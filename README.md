# SafeAgent_Manager

정책 기반으로 LLM 응답을 평가하고, 위반 시 `BLOCK` 또는 `LOG` 등의 조치를 수행하는 FastAPI 기반 거버넌스 엔진입니다.

현재 저장소는 **기존 구조를 유지하면서** 아래 방향으로 확장 중입니다.

- Feature 1: Query Risk Detection
- Feature 2: Response Compliance Validation
- Feature 3: Policy Document Conversion (`.docx -> YAML`)
- DB: SQLite 기반에서 **PostgreSQL 기반으로 전환 중**

## 현재 주요 API

- `GET /health`
- `POST /api/v1/evaluate`
- `GET /api/v1/runs/{run_id}`
- `GET /api/v1/runs/{run_id}/trace`
- `GET /api/v1/violations`
- `GET /api/v1/audit-logs`

추가된 신규 뼈대 파일:

- `src/routers/query_check.py`
- `src/routers/response_validate.py`
- `src/routers/policy_convert.py`
- `src/workflows/query_risk_workflow.py`
- `src/workflows/compliance_workflow.py`
- `src/workflows/doc_parser_workflow.py`

## 프로젝트 구조

```text
src/
├─ main.py
├─ main_query.py
├─ main_policy.py
├─ core/
├─ database/
├─ engines/
├─ policies/
├─ prompts/
├─ routers/
├─ schemas/
├─ services/
├─ utils/
└─ workflows/

tests/
├─ integration/
└─ ...
```

## Swagger 주소

현재 Docker 방식과 로컬 방식 모두 아래 주소를 사용합니다.

- [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

## 실행 방법

이 프로젝트는 **Docker 방식**과 **로컬 방식** 두 가지로 실행할 수 있습니다.

---

## 1. Docker 방식

### 사용 대상

- Docker Desktop이 설치되어 있는 경우
- API와 PostgreSQL을 함께 띄우고 싶은 경우

### 실행 명령

프로젝트 루트에서:

```powershell
docker compose up -d --build
```

### Docker 구성 정보

- PostgreSQL 버전: `16` (`postgres:16`)
- API 포트: `8000`
- PostgreSQL 포트: `5432`
- PostgreSQL DB: `safeagent`
- PostgreSQL User: `safeagent_app`
- PostgreSQL Password: `safeagent_password`

### 참고

Docker 내부 API 컨테이너는 DB에 아래 주소로 연결됩니다.

```text
postgresql://safeagent_app:safeagent_password@postgres:5432/safeagent
```

여기서 `postgres`는 Docker Compose 서비스명입니다.

---

## 2. 로컬 방식

### 사용 대상

- Docker 없이 Python + 로컬 PostgreSQL로 실행하고 싶은 경우

### 사전 준비

1. Python 패키지 설치

```powershell
pip install -r requirements.txt
```

2. 로컬 PostgreSQL 설치

- 권장 설치 파일: `postgresql-18.3-windows-x64.exe`
- 설치 중에는 **기본값을 유지하고 Port만 `5433`으로 변경**하는 것을 권장합니다.

권장 설치 기준:

- Installation Directory: 기본값 사용
- Components: 기본값 사용
- Data Directory: 기본값 사용
- Password: 본인이 기억할 수 있는 값 입력
- Port: **`5433`**
- Locale: 기본값 사용
- Stack Builder: **추가 설치 없이 건너뛰기**

3. 로컬 PostgreSQL 서비스 실행 확인

PowerShell에서:

```powershell
Get-Service *postgres*
```

정상 예시:

```text
Status   Name               DisplayName
------   ----               -----------
Running  postgresql-x64-18  postgresql-x64-18
```

만약 `Running`이 아니면:

```powershell
Start-Service postgresql-x64-18
```

4. 로컬 PostgreSQL 접속 정보

- PostgreSQL 버전: `18.3 for Windows`
- Host: `localhost`
- Port: `5433`
- 기본 접속 DB: `postgres`
- User: `postgres`

5. `safeagent` 데이터베이스 생성

DBeaver 또는 pgAdmin에서 기본 DB `postgres`로 접속한 뒤 아래 SQL을 실행합니다.

```sql
CREATE DATABASE safeagent;
```

6. 프로젝트 루트에 `.env` 파일 생성

예시:

```env
APP_NAME=SafeAgent_Manager
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5433/safeagent
POLICY_DIR=src/policies
PROMPT_DIR=src/prompts
WORKFLOW_NAME=governance_workflow
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_TEMPERATURE=0.1
```

7. 서버 실행

```powershell
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

### 참고

- 로컬 방식은 `.env` 값을 읽어서 DB에 연결합니다.
- `.env.example`은 예시 파일이고, 실제 실행에는 `.env`를 사용합니다.
- 로컬 PostgreSQL 포트를 `5433`으로 두는 이유는 Docker PostgreSQL 기본 포트 `5432`와 충돌을 피하기 위해서입니다.

---

## Docker 방식과 로컬 방식 차이

### Docker 방식

- API와 PostgreSQL을 함께 실행
- DB 주소는 `postgres:5432`
- `docker-compose.yml` 기준으로 동작

### 로컬 방식

- API는 로컬 `uvicorn`으로 실행
- DB는 로컬 PostgreSQL에 직접 연결
- DB 주소는 `localhost:5433`

---

## 자주 헷갈리는 포인트

### 1. Swagger 주소가 왜 하나인가요?

현재 Docker 방식과 로컬 방식 모두 API 포트를 `8000`으로 맞춰두었습니다.

그래서 실행 방식은 달라도 접속 주소는 동일합니다.

### 2. Docker가 없으면 Swagger를 못 띄우나요?

아닙니다.

- Docker 방식은 Docker가 필요합니다.
- 로컬 방식은 Docker 없이도 실행할 수 있습니다.

단, 로컬 방식에서는 PostgreSQL과 `.env` 설정이 먼저 준비되어 있어야 합니다.

### 3. `.env.example`에 적으면 되나요?

아니요.

- `.env.example`: 예시 파일
- `.env`: 실제 실행 파일

실제 비밀번호와 로컬 DB 주소는 `.env`에 넣어야 합니다.

### 4. PostgreSQL이 없어도 Swagger만 확인할 수 있나요?

현재 코드는 DB가 없어도 서버와 Swagger가 뜨도록 보완되어 있습니다.

다만 DB가 없는 상태에서는:

- `GET /health`
- Swagger 문서 확인

은 가능하지만, DB 저장/조회가 필요한 API는 정상 동작하지 않을 수 있습니다.

## 테스트

```powershell
pytest
```

## 현재 상태 참고

- PostgreSQL 연결용 코드와 모델은 1차 반영 완료
- Feature 1/2/3 신규 파일 뼈대 추가 완료
- 실제 세부 로직 연결 및 DB 저장 흐름은 계속 확장 중

# SafeAgent Manager 배포 가이드

## 1. 배포 파일 준비
- `safeagent-deployment-bundle.zip` 파일을 다운로드하고 압축을 해제합니다.
- `.env.release.example` 파일을 `.env`로 복사한 뒤 회사 환경에 맞게 수정합니다.
- `docker-compose.release.yml` 파일의 이미지 태그와 포트를 확인합니다.

## 2. 서버 환경 준비
- Docker Engine과 Docker Compose를 설치합니다.
- `3000`, `8000`, `5432` 포트 사용 가능 여부를 확인합니다.
- 사내 방화벽과 저장 경로 권한을 점검합니다.

## 3. 권장 설치 방법
### Windows 서버
```bat
install.bat
```

### Linux 서버
```bash
chmod +x install.sh
./install.sh
```

`install` 스크립트는 같은 폴더에 `safeagent-api-v0.2.0.tar`, `safeagent-portal-v0.2.0.tar`가 있으면 오프라인 설치를 우선 사용하고, 없으면 온라인 레지스트리에서 이미지를 가져옵니다.

## 4. 오프라인 이미지 준비
### Windows
```powershell
powershell -ExecutionPolicy Bypass -File prepare-release-images.ps1
```

### Linux
```bash
chmod +x prepare-release-images.sh
./prepare-release-images.sh
```

이 스크립트는 실제 배포 이미지를 내려받아 `.tar` 파일로 저장합니다.

### 저장소에서 직접 이미지 생성
배포 담당자가 현재 저장소에서 실제 이미지를 직접 만들고 싶다면 아래 스크립트를 사용합니다.

#### Windows
```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_release_images.ps1
```

#### Linux
```bash
chmod +x scripts/build_release_images.sh
./scripts/build_release_images.sh
```

이 스크립트는 `frontend/downloads/` 폴더에 `safeagent-api-v0.2.0.tar`, `safeagent-portal-v0.2.0.tar`를 생성합니다.

## 5. 수동 반영이 필요한 경우
### 온라인 레지스트리 사용 시
```bash
docker compose -f docker-compose.release.yml pull
docker compose -f docker-compose.release.yml up -d
```

### 오프라인 이미지 사용 시
```bash
docker load -i safeagent-api-v0.2.0.tar
docker load -i safeagent-portal-v0.2.0.tar
docker compose -f docker-compose.release.yml up -d
```

## 6. 마이그레이션 실행
```bash
docker compose -f docker-compose.release.yml exec api python -m scripts.run_migrations
```

## 7. 반영 결과 확인
- `http://<server>:3000`에서 배포 포털 화면이 열리는지 확인합니다.
- `http://<server>:8000/health`에서 API 상태를 확인합니다.
- 정책 파일과 데이터베이스 연결이 정상인지 확인합니다.

## 8. 롤백 계획
- 직전 안정 버전 이미지 태그를 보관합니다.
- 헬스체크 실패 시 이전 이미지 태그로 되돌린 뒤 서비스를 다시 시작합니다.

#!/usr/bin/env sh
set -eu

echo "[SafeAgent] Linux 배포를 시작합니다."

if [ ! -f ".env" ]; then
  if [ -f ".env.release.example" ]; then
    cp .env.release.example .env
    echo "[SafeAgent] .env 파일을 생성했습니다. 필요 시 값을 수정하세요."
  else
    echo "[SafeAgent] .env.release.example 파일이 없습니다."
    exit 1
  fi
fi

if [ -f "safeagent-api-v0.2.0.tar" ]; then
  echo "[SafeAgent] 오프라인 API 이미지를 불러옵니다."
  docker load -i safeagent-api-v0.2.0.tar
else
  echo "[SafeAgent] 온라인 레지스트리에서 API 이미지를 가져옵니다."
  docker compose -f docker-compose.release.yml pull api
fi

if [ -f "safeagent-portal-v0.2.0.tar" ]; then
  echo "[SafeAgent] 오프라인 프론트 이미지를 불러옵니다."
  docker load -i safeagent-portal-v0.2.0.tar
else
  echo "[SafeAgent] 온라인 레지스트리에서 프론트 이미지를 가져옵니다."
  docker compose -f docker-compose.release.yml pull frontend
fi

docker compose -f docker-compose.release.yml up -d

echo "[SafeAgent] 컨테이너를 올렸습니다. 마이그레이션을 진행합니다."
docker compose -f docker-compose.release.yml exec api python -m scripts.run_migrations

echo "[SafeAgent] 배포가 완료되었습니다."
